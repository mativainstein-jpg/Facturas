// Bot de Telegram: recibe el Excel de proveedores y actualiza los maestros
// (cuit_nombre.xlsx / proveedores.xlsx) en GitHub, sin revisión humana.
//
// Variables de entorno necesarias (configurar en Vercel):
//   TELEGRAM_BOT_TOKEN     - token del bot (de @BotFather)
//   TELEGRAM_SECRET_TOKEN  - secreto random propio, para validar que el
//                            pedido viene realmente de Telegram
//   AUTHORIZED_TELEGRAM_ID - ID numérico de Telegram autorizado a mandar
//                            el archivo (de @userinfobot)
//   GITHUB_TOKEN           - Personal Access Token con permiso de escritura
//                            sobre el repo
//   GITHUB_OWNER           - "mativainstein-jpg"
//   GITHUB_REPO            - "Facturas"
//   TARGET_BRANCHES        - ramas a actualizar, separadas por coma
//                            (ej. "main,claude/invoice-app-setup-ss5uwf,
//                            claude/bejerman-invoice-reader-do4scq")

import * as XLSX from 'xlsx';

const GITHUB_API = 'https://api.github.com';
const MIN_FILAS_VALIDAS = 100; // debajo de esto, se sospecha archivo incorrecto

// ---------------------------------------------------------------------------
// Parseo del archivo que manda el administrativo
// ---------------------------------------------------------------------------

function parsearArchivoNuevo(buffer) {
  const wb = XLSX.read(buffer, { type: 'buffer' });
  const sheet = wb.Sheets[wb.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: true, defval: '' });
  if (!rows.length) throw new Error('El archivo está vacío.');

  const headers = rows[0].map((h) => String(h).trim().toLowerCase());
  const idxCuit = headers.indexOf('cuit');
  const idxNombre = headers.indexOf('nombre');
  const idxGasto = headers.indexOf('codgasto');
  const idxRubro = headers.indexOf('codrubro');
  if (idxCuit === -1 || idxNombre === -1 || idxGasto === -1 || idxRubro === -1) {
    throw new Error(
      'El archivo no tiene las columnas esperadas (cuit, nombre, codgasto, codrubro). ' +
      '¿Es el Excel de proveedores correcto?'
    );
  }

  const nuevo = new Map();
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const cuit = String(row[idxCuit] ?? '').replace(/\D/g, '');
    if (cuit.length !== 11) continue;
    const nombre = String(row[idxNombre] ?? '').trim();
    const gastoRaw = row[idxGasto];
    const rubroRaw = row[idxRubro];
    const gasto = gastoRaw === '' || gastoRaw == null ? null : Number(gastoRaw);
    const rubro = rubroRaw === '' || rubroRaw == null ? null : Number(rubroRaw);
    nuevo.set(cuit, { nombre, gasto, rubro });
  }

  if (nuevo.size < MIN_FILAS_VALIDAS) {
    throw new Error(
      `Solo encontré ${nuevo.size} filas con CUIT válido (esperaba miles). ` +
      'No actualicé nada — revisá que sea el archivo correcto.'
    );
  }
  return nuevo;
}

// ---------------------------------------------------------------------------
// Fusión con los maestros (misma lógica que se venía aplicando a mano)
// ---------------------------------------------------------------------------

function indexarPorCuit(rows) {
  const filaPorCuit = new Map();
  for (let i = 1; i < rows.length; i++) {
    const raw = rows[i][0];
    if (raw) {
      const c = String(raw).replace(/\D/g, '');
      if (c) filaPorCuit.set(c, i);
    }
  }
  return filaPorCuit;
}

function actualizarNombres(rows, nuevoMap) {
  const filaPorCuit = indexarPorCuit(rows);
  let agregados = 0;
  let corregidos = 0;
  for (const [cuit, d] of nuevoMap) {
    if (!d.nombre) continue;
    if (filaPorCuit.has(cuit)) {
      const i = filaPorCuit.get(cuit);
      const actual = String(rows[i][1] ?? '').trim();
      if (actual !== d.nombre) {
        rows[i][1] = d.nombre;
        corregidos++;
      }
    } else {
      rows.push([cuit, d.nombre]);
      agregados++;
    }
  }
  return { agregadosNombre: agregados, corregidosNombre: corregidos };
}

function actualizarProveedores(rows, nuevoMap) {
  const filaPorCuit = indexarPorCuit(rows);
  let agregados = 0;
  let corregidos = 0;
  for (const [cuit, d] of nuevoMap) {
    if (d.gasto == null && d.rubro == null) continue;
    if (filaPorCuit.has(cuit)) {
      const i = filaPorCuit.get(cuit);
      const row = rows[i];
      const gActual = row[1] === '' || row[1] == null ? null : Number(row[1]);
      const ruActual = row[3] === '' || row[3] == null ? null : Number(row[3]);
      if (gActual !== d.gasto || ruActual !== d.rubro) {
        row[1] = d.gasto;
        row[3] = d.rubro;
        corregidos++;
      }
    } else {
      rows.push([cuit, d.gasto, null, d.rubro]);
      agregados++;
    }
  }
  return { agregadosProv: agregados, corregidosProv: corregidos };
}

// ---------------------------------------------------------------------------
// GitHub: leer/escribir los maestros por rama (commit atómico vía Git Data API)
// ---------------------------------------------------------------------------

async function ghFetch(path, opts = {}) {
  const res = await fetch(`${GITHUB_API}${path}`, {
    ...opts,
    headers: {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GitHub API ${path} -> ${res.status}: ${body.slice(0, 300)}`);
  }
  return res.json();
}

async function leerXlsxDeRama(owner, repo, branch, path) {
  const data = await ghFetch(`/repos/${owner}/${repo}/contents/${path}?ref=${branch}`);
  const buf = Buffer.from(data.content, 'base64');
  const wb = XLSX.read(buf, { type: 'buffer' });
  const sheetName = wb.SheetNames[0];
  const rows = XLSX.utils.sheet_to_json(wb.Sheets[sheetName], { header: 1, raw: true, defval: '' });
  return { rows, sheetName };
}

function serializarXlsx(rows, sheetName) {
  const ws = XLSX.utils.aoa_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
}

async function actualizarRama(owner, repo, branch, nuevoMap) {
  const { rows: rowsNombres, sheetName: sheetNombres } = await leerXlsxDeRama(
    owner, repo, branch, 'cuit_nombre.xlsx'
  );
  const { rows: rowsProv, sheetName: sheetProv } = await leerXlsxDeRama(
    owner, repo, branch, 'proveedores.xlsx'
  );

  const rNombres = actualizarNombres(rowsNombres, nuevoMap);
  const rProv = actualizarProveedores(rowsProv, nuevoMap);
  const totalCambios =
    rNombres.agregadosNombre + rNombres.corregidosNombre +
    rProv.agregadosProv + rProv.corregidosProv;

  const resumen = { branch, ...rNombres, ...rProv };

  if (totalCambios === 0) {
    return { ...resumen, sinCambios: true };
  }

  const outNombres = serializarXlsx(rowsNombres, sheetNombres);
  const outProv = serializarXlsx(rowsProv, sheetProv);

  const ref = await ghFetch(`/repos/${owner}/${repo}/git/ref/heads/${branch}`);
  const latestCommitSha = ref.object.sha;
  const latestCommit = await ghFetch(`/repos/${owner}/${repo}/git/commits/${latestCommitSha}`);
  const baseTreeSha = latestCommit.tree.sha;

  const blobNombres = await ghFetch(`/repos/${owner}/${repo}/git/blobs`, {
    method: 'POST',
    body: JSON.stringify({ content: outNombres.toString('base64'), encoding: 'base64' }),
  });
  const blobProv = await ghFetch(`/repos/${owner}/${repo}/git/blobs`, {
    method: 'POST',
    body: JSON.stringify({ content: outProv.toString('base64'), encoding: 'base64' }),
  });

  const newTree = await ghFetch(`/repos/${owner}/${repo}/git/trees`, {
    method: 'POST',
    body: JSON.stringify({
      base_tree: baseTreeSha,
      tree: [
        { path: 'cuit_nombre.xlsx', mode: '100644', type: 'blob', sha: blobNombres.sha },
        { path: 'proveedores.xlsx', mode: '100644', type: 'blob', sha: blobProv.sha },
      ],
    }),
  });

  const mensaje =
    `Actualizar maestros de proveedores vía Telegram ` +
    `(${rNombres.agregadosNombre + rProv.agregadosProv} nuevos, ` +
    `${rNombres.corregidosNombre + rProv.corregidosProv} corregidos)\n\n` +
    `Enviado por Telegram, aplicado sin revisión.`;

  const newCommit = await ghFetch(`/repos/${owner}/${repo}/git/commits`, {
    method: 'POST',
    body: JSON.stringify({ message: mensaje, tree: newTree.sha, parents: [latestCommitSha] }),
  });

  await ghFetch(`/repos/${owner}/${repo}/git/refs/heads/${branch}`, {
    method: 'PATCH',
    body: JSON.stringify({ sha: newCommit.sha }),
  });

  return { ...resumen, sinCambios: false };
}

// ---------------------------------------------------------------------------
// Telegram
// ---------------------------------------------------------------------------

function tgApi(path) {
  return `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}${path}`;
}

async function tgSendMessage(chatId, text) {
  await fetch(tgApi('/sendMessage'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}

async function tgGetFileBuffer(fileId) {
  const info = await (await fetch(tgApi(`/getFile?file_id=${fileId}`))).json();
  if (!info.ok) throw new Error('No pude descargar el archivo de Telegram.');
  const fileUrl = `https://api.telegram.org/file/bot${process.env.TELEGRAM_BOT_TOKEN}/${info.result.file_path}`;
  const res = await fetch(fileUrl);
  return Buffer.from(await res.arrayBuffer());
}

// ---------------------------------------------------------------------------
// Handler principal
// ---------------------------------------------------------------------------

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(200).send('OK');
    return;
  }

  // Confirmar que el pedido viene realmente de Telegram (no de cualquiera
  // que adivine la URL del webhook).
  const secretHeader = req.headers['x-telegram-bot-api-secret-token'];
  if (secretHeader !== process.env.TELEGRAM_SECRET_TOKEN) {
    res.status(401).send('unauthorized');
    return;
  }

  // Responder rápido a Telegram (si no, reintenta el mismo update) y seguir
  // procesando después.
  res.status(200).send('OK');

  const message = req.body && req.body.message;
  if (!message) return;

  const chatId = message.chat.id;
  const fromId = message.from && message.from.id;

  if (String(fromId) !== process.env.AUTHORIZED_TELEGRAM_ID) {
    return; // ignorar silenciosamente a cualquiera que no sea la persona autorizada
  }

  if (!message.document) {
    await tgSendMessage(chatId, 'Mandame el Excel de proveedores como archivo adjunto (no como foto ni texto).');
    return;
  }

  try {
    const buffer = await tgGetFileBuffer(message.document.file_id);
    const nuevoMap = parsearArchivoNuevo(buffer);

    const owner = process.env.GITHUB_OWNER;
    const repo = process.env.GITHUB_REPO;
    const ramas = (process.env.TARGET_BRANCHES || 'main').split(',').map((s) => s.trim()).filter(Boolean);

    const resultados = [];
    for (const branch of ramas) {
      resultados.push(await actualizarRama(owner, repo, branch, nuevoMap));
    }

    const r0 = resultados[0];
    const nuevos = r0.agregadosNombre + r0.agregadosProv;
    const corregidos = r0.corregidosNombre + r0.corregidosProv;

    let resumen;
    if (nuevos + corregidos === 0) {
      resumen = `ℹ️ Revisé ${nuevoMap.size} proveedores, no había nada nuevo para actualizar.`;
    } else {
      resumen =
        `✅ Proveedores actualizados (leí ${nuevoMap.size} filas):\n` +
        `• ${nuevos} nuevos\n` +
        `• ${corregidos} corregidos\n` +
        `Ramas actualizadas: ${resultados.map((r) => r.branch).join(', ')}`;
    }
    await tgSendMessage(chatId, resumen);
  } catch (err) {
    await tgSendMessage(chatId, `❌ No pude actualizar: ${err.message}`);
  }
}
