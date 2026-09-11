const bannerErro = document.getElementById('banner-erro');

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function esc(valor) {
  return String(valor ?? '').replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

function mostrarErro(msg) {
  bannerErro.textContent = msg;
  bannerErro.hidden = false;
}

function esconderErro() {
  bannerErro.hidden = true;
}

async function pedirJSON(url, opts) {
  const resp = await fetch(url, opts);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.erro || `Erro ${resp.status}`);
  }
  return data;
}

function formatarEquipa(nome, logo, visitante) {
  const img = logo ? `<img class="escudo" src="${esc(logo)}" alt="" loading="lazy">` : '';
  const span = `<span class="nome-equipa">${esc(nome)}</span>`;
  return `<div class="equipa${visitante ? ' equipa-visitante' : ''}">${img}${span}</div>`;
}

function renderClassificacao(linhas) {
  const corpo = document.getElementById('corpo-classificacao');
  corpo.innerHTML = linhas.map((l, i) => `
    <tr>
      <td class="col-pos">${i + 1}</td>
      <td class="col-clube">
        <div class="linha-clube">
          ${l.logo_url ? `<img class="escudo" src="${esc(l.logo_url)}" alt="" loading="lazy">` : ''}
          <span>${esc(l.nome)}</span>
        </div>
      </td>
      <td>${l.jogos}</td>
      <td>${l.vitorias}</td>
      <td>${l.empates}</td>
      <td>${l.derrotas}</td>
      <td>${l.golos_marcados}</td>
      <td>${l.golos_sofridos}</td>
      <td>${l.diferenca > 0 ? '+' : ''}${l.diferenca}</td>
      <td class="col-pontos">${l.pontos}</td>
    </tr>
  `).join('');
}

function renderJogo(jogo) {
  const jogado = jogo.jogado;
  const placar = jogado
    ? `<span class="golos">${jogo.golos_casa}</span><span class="separador">&ndash;</span><span class="golos">${jogo.golos_visitante}</span>`
    : `<span>${new Date(jogo.data_jogo).toLocaleDateString('pt-PT')}</span>`;

  let detalhe = '';
  if (jogado) {
    const eventos = [];
    jogo.golos.forEach(g => {
      eventos.push(`<span class="evento golo">${esc(g.jogador)} ${g.minuto}&prime;</span>`);
    });
    jogo.cartoes.forEach(c => {
      eventos.push(`<span class="evento"><span class="cartao-tag ${esc(c.tipo_cartao)}"></span>${esc(c.jogador)} ${c.minuto}&prime;</span>`);
    });
    detalhe = eventos.length
      ? `<div class="jogo-detalhe">${eventos.join('')}</div>`
      : `<div class="jogo-detalhe"><span class="evento">Sem golos nem cartões</span></div>`;
  }

  return `
    <div class="jogo" data-jogado="${jogado}">
      <div class="jogo-equipas">
        ${formatarEquipa(jogo.casa, jogo.casa_logo, false)}
        <div class="placar">${placar}</div>
        ${formatarEquipa(jogo.visitante, jogo.visitante_logo, true)}
      </div>
      ${detalhe}
    </div>
  `;
}

function renderJornadas(jornadas) {
  const container = document.getElementById('jornadas');
  const vazio = document.getElementById('estado-vazio');

  if (!jornadas.length) {
    vazio.hidden = false;
    container.innerHTML = '';
    return;
  }
  vazio.hidden = true;

  container.innerHTML = jornadas.map(j => {
    const todasJogadas = j.jogos.every(jg => jg.jogado);
    const acao = todasJogadas
      ? ''
      : `<div class="jornada-acao"><button class="btn btn-ouro btn-simular" data-numero="${j.numero}">&#9654; Simular jornada ${j.numero}</button></div>`;

    return `
      <article class="jornada" data-numero="${j.numero}">
        <div class="jornada-cabecalho">
          <span class="jornada-numero">${j.numero}</span>
          <h3>Jornada ${j.numero}</h3>
          <span class="jornada-estado">${todasJogadas ? 'Jogada' : 'Por jogar'}</span>
        </div>
        <div class="lista-jogos">
          ${j.jogos.map(renderJogo).join('')}
        </div>
        ${acao}
      </article>
    `;
  }).join('');

  container.querySelectorAll('.btn-simular').forEach(btn => {
    btn.addEventListener('click', () => simularJornada(Number(btn.dataset.numero)));
  });
}

async function carregarTudo() {
  esconderErro();
  const [classificacao, jornadas] = await Promise.all([
    pedirJSON('/api/classificacao'),
    pedirJSON('/api/jornadas'),
  ]);
  renderClassificacao(classificacao);
  renderJornadas(jornadas);
}

async function gerarCalendario() {
  const btn = document.getElementById('btn-gerar-calendario');
  btn.disabled = true;
  try {
    await pedirJSON('/api/calendario/gerar', { method: 'POST' });
    await carregarTudo();
  } catch (e) {
    mostrarErro(e.message);
  } finally {
    btn.disabled = false;
  }
}

async function simularJornada(numero) {
  const btn = document.querySelector(`.btn-simular[data-numero="${numero}"]`);
  if (btn) { btn.disabled = true; btn.textContent = 'A simular…'; }
  try {
    await pedirJSON(`/api/jornadas/${numero}/simular`, { method: 'POST' });
    await carregarTudo();
    const jornadaEl = document.querySelector(`.jornada[data-numero="${numero}"]`);
    if (jornadaEl) {
      jornadaEl.classList.add('jornada-revelada');
      jornadaEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  } catch (e) {
    mostrarErro(e.message);
    if (btn) { btn.disabled = false; btn.textContent = `▶ Simular jornada ${numero}`; }
  }
}

async function reiniciarEpoca() {
  if (!confirm('Isto apaga todas as jornadas, jogos, golos e cartões desta época. Continuar?')) return;
  try {
    await pedirJSON('/api/epoca/reiniciar', { method: 'POST' });
    await carregarTudo();
  } catch (e) {
    mostrarErro(e.message);
  }
}

document.getElementById('btn-gerar-calendario').addEventListener('click', gerarCalendario);
document.getElementById('btn-reiniciar').addEventListener('click', reiniciarEpoca);

carregarTudo().catch(e => mostrarErro(e.message));
