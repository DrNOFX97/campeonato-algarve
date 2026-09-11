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

// ------------------------------------------------------------------
// Classificação
// ------------------------------------------------------------------

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

// ------------------------------------------------------------------
// Jornadas
// ------------------------------------------------------------------

function renderJogo(jogo) {
  const jogado = jogo.jogado;
  const placar = jogado
    ? `<span class="golos">${jogo.golos_casa}</span><span class="separador">&ndash;</span><span class="golos">${jogo.golos_visitante}</span>`
    : `<span>${new Date(jogo.data_jogo).toLocaleDateString('pt-PT')}</span>`;

  let detalhe = '';
  if (jogado) {
    const eventosPorLado = (lado) => {
      const invertido = lado === 'casa';
      const golos = jogo.golos
        .filter(g => g.lado === lado)
        .map(g => ({
          minuto: g.minuto,
          html: invertido
            ? `<span class="evento golo-esq">${g.minuto}&prime; ${esc(g.jogador)}</span>`
            : `<span class="evento golo">${esc(g.jogador)} ${g.minuto}&prime;</span>`,
        }));
      const cartoes = jogo.cartoes
        .filter(c => c.lado === lado)
        .map(c => ({
          minuto: c.minuto,
          html: invertido
            ? `<span class="evento">${c.minuto}&prime; ${esc(c.jogador)} <span class="cartao-tag ${esc(c.tipo_cartao)}"></span></span>`
            : `<span class="evento"><span class="cartao-tag ${esc(c.tipo_cartao)}"></span>${esc(c.jogador)} ${c.minuto}&prime;</span>`,
        }));
      const todos = golos.concat(cartoes).sort((a, b) => a.minuto - b.minuto);
      return todos.length ? todos.map(e => e.html).join('') : '<span class="evento evento-vazio">&mdash;</span>';
    };

    detalhe = `
      <div class="jogo-detalhe">
        <div class="detalhe-lado detalhe-casa">${eventosPorLado('casa')}</div>
        <div class="detalhe-lado detalhe-visitante">${eventosPorLado('visitante')}</div>
      </div>
    `;
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

async function gerarCalendario() {
  const btn = document.getElementById('btn-gerar-calendario');
  btn.disabled = true;
  try {
    await pedirJSON('/api/calendario/gerar', { method: 'POST' });
    await carregarPainel('jornadas');
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
    await carregarPainel('jornadas');
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
    jogadoresPromise = null;
    await carregarPainel(painelAtivo);
  } catch (e) {
    mostrarErro(e.message);
  }
}

// ------------------------------------------------------------------
// Jogadores
// ------------------------------------------------------------------

let jogadoresPromise = null;
function obterJogadores() {
  if (!jogadoresPromise) jogadoresPromise = pedirJSON('/api/jogadores');
  return jogadoresPromise;
}

let jogadoresCarregados = [];
let filtrosJogadoresProntos = false;

function popularSelect(select, valores) {
  const atual = select.value;
  const primeira = select.options[0];
  select.innerHTML = primeira.outerHTML + valores.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
  if (valores.includes(atual)) select.value = atual;
}

function aplicarFiltrosJogadores() {
  const nomeQuery = document.getElementById('filtro-jogador-nome').value.trim().toLowerCase();
  const clube = document.getElementById('filtro-jogador-clube').value;
  const posicao = document.getElementById('filtro-jogador-posicao').value;
  const nac = document.getElementById('filtro-jogador-nacionalidade').value;

  const filtrados = jogadoresCarregados.filter(j =>
    (!nomeQuery || j.nome.toLowerCase().includes(nomeQuery)) &&
    (!clube || j.clube === clube) &&
    (!posicao || j.posicao === posicao) &&
    (!nac || j.nacionalidade === nac)
  );

  document.getElementById('contagem-jogadores').textContent =
    `${filtrados.length} de ${jogadoresCarregados.length} jogadores`;

  document.getElementById('corpo-jogadores').innerHTML = filtrados.map(j => `
    <tr>
      <td>${j.numero_camisola ?? '—'}</td>
      <td>${esc(j.nome)}</td>
      <td>
        <div class="linha-clube">
          ${j.clube_logo ? `<img class="escudo" src="${esc(j.clube_logo)}" alt="" loading="lazy">` : ''}
          <span>${esc(j.clube)}</span>
        </div>
      </td>
      <td>${esc(j.posicao)}</td>
      <td>${esc(j.nacionalidade)}</td>
      <td>${new Date(j.data_nascimento).toLocaleDateString('pt-PT')}</td>
    </tr>
  `).join('');
}

async function carregarJogadores() {
  jogadoresCarregados = await obterJogadores();

  popularSelect(document.getElementById('filtro-jogador-clube'), [...new Set(jogadoresCarregados.map(j => j.clube))].sort());
  popularSelect(document.getElementById('filtro-jogador-posicao'), [...new Set(jogadoresCarregados.map(j => j.posicao))].sort());
  popularSelect(document.getElementById('filtro-jogador-nacionalidade'), [...new Set(jogadoresCarregados.map(j => j.nacionalidade))].sort());

  if (!filtrosJogadoresProntos) {
    document.getElementById('filtro-jogador-nome').addEventListener('input', aplicarFiltrosJogadores);
    document.getElementById('filtro-jogador-clube').addEventListener('change', aplicarFiltrosJogadores);
    document.getElementById('filtro-jogador-posicao').addEventListener('change', aplicarFiltrosJogadores);
    document.getElementById('filtro-jogador-nacionalidade').addEventListener('change', aplicarFiltrosJogadores);
    filtrosJogadoresProntos = true;
  }

  aplicarFiltrosJogadores();
}

// ------------------------------------------------------------------
// Clubes
// ------------------------------------------------------------------

async function alternarPlantel(idClube, container, botao) {
  if (container.dataset.carregado) {
    container.hidden = !container.hidden;
    botao.textContent = container.hidden ? 'Ver plantel' : 'Esconder plantel';
    return;
  }
  const jogadores = (await obterJogadores()).filter(j => j.id_clube === idClube);
  container.innerHTML = jogadores.map(j => `
    <div class="linha-plantel">
      <span class="plantel-numero">${j.numero_camisola ?? '—'}</span>
      <span class="plantel-nome">${esc(j.nome)}</span>
      <span class="plantel-posicao">${esc(j.posicao)}</span>
    </div>
  `).join('');
  container.dataset.carregado = '1';
  container.hidden = false;
  botao.textContent = 'Esconder plantel';
}

async function carregarClubes() {
  const clubes = await pedirJSON('/api/clubes');
  const container = document.getElementById('grelha-clubes');

  container.innerHTML = clubes.map(c => `
    <article class="cartao-clube">
      <div class="cartao-clube-cabecalho">
        ${c.logo_url ? `<img class="escudo escudo-grande" src="${esc(c.logo_url)}" alt="" loading="lazy">` : ''}
        <div>
          <h3>${esc(c.nome)}</h3>
          <p class="cartao-clube-sub">${esc(c.cidade)}</p>
          <p class="cartao-clube-sub">Fundado em ${c.ano_fundacao}</p>
        </div>
      </div>
      <dl class="cartao-clube-dados">
        <div><dt>Estádio</dt><dd>${esc(c.estadio || '—')}</dd></div>
        <div><dt>Treinador</dt><dd>${esc(c.treinador || 'por anunciar')}</dd></div>
        <div><dt>Plantel</dt><dd>${c.n_jogadores} jogadores</dd></div>
      </dl>
      <div class="cartao-clube-stats">
        <div><span class="stat-valor">${c.pontos}</span><span class="stat-label">Pts</span></div>
        <div><span class="stat-valor">${c.jogos}</span><span class="stat-label">J</span></div>
        <div><span class="stat-valor">${c.vitorias}</span><span class="stat-label">V</span></div>
        <div><span class="stat-valor">${c.empates}</span><span class="stat-label">E</span></div>
        <div><span class="stat-valor">${c.derrotas}</span><span class="stat-label">D</span></div>
        <div><span class="stat-valor">${c.golos_marcados}-${c.golos_sofridos}</span><span class="stat-label">Golos</span></div>
      </div>
      <button class="btn btn-fantasma btn-ver-plantel" data-id="${c.id_clube}">Ver plantel</button>
      <div class="cartao-clube-plantel" id="plantel-${c.id_clube}" hidden></div>
    </article>
  `).join('');

  container.querySelectorAll('.btn-ver-plantel').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = Number(btn.dataset.id);
      alternarPlantel(id, document.getElementById(`plantel-${id}`), btn);
    });
  });
}

// ------------------------------------------------------------------
// Estatísticas
// ------------------------------------------------------------------

function graficoBarras(container, itens, opcoes) {
  if (!itens.length) {
    container.innerHTML = '<p class="grafico-vazio">Sem dados ainda — simula algumas jornadas.</p>';
    return;
  }
  const max = Math.max(...itens.map(i => i.valor), 1);
  container.innerHTML = itens.map(item => `
    <div class="barra-linha">
      <span class="barra-rotulo">${opcoes.formatarLabel(item)}</span>
      <div class="barra-trilho"><div class="barra-preenchimento" style="width:${Math.round((item.valor / max) * 100)}%"></div></div>
      <span class="barra-valor">${opcoes.formatarValor(item)}</span>
    </div>
  `).join('');
}

async function carregarEstatisticas() {
  const dados = await pedirJSON('/api/estatisticas');
  const r = dados.resumo;

  document.getElementById('resumo-estatisticas').innerHTML = `
    <div class="stat-tile"><span class="stat-tile-valor">${r.jogos_jogados}/${r.total_jogos}</span><span class="stat-tile-label">Jogos disputados</span></div>
    <div class="stat-tile"><span class="stat-tile-valor">${r.total_golos}</span><span class="stat-tile-label">Golos marcados</span></div>
    <div class="stat-tile"><span class="stat-tile-valor">${r.media_golos_por_jogo ?? '—'}</span><span class="stat-tile-label">Média golos / jogo</span></div>
    <div class="stat-tile"><span class="stat-tile-valor">${r.amarelos}</span><span class="stat-tile-label">Cartões amarelos</span></div>
    <div class="stat-tile"><span class="stat-tile-valor">${r.vermelhos}</span><span class="stat-tile-label">Cartões vermelhos</span></div>
  `;

  const comEscudo = (item) => item.clube_logo ? `<img class="escudo-mini" src="${esc(item.clube_logo)}" alt="">` : '';

  graficoBarras(
    document.getElementById('grafico-marcadores'),
    dados.topo_marcadores.map(m => ({ ...m, valor: m.golos })),
    { formatarLabel: m => `${comEscudo(m)}${esc(m.jogador)}`, formatarValor: m => m.golos }
  );

  graficoBarras(
    document.getElementById('grafico-cartoes'),
    dados.topo_cartoes.map(c => ({ ...c, valor: c.total })),
    {
      formatarLabel: c => `${comEscudo(c)}${esc(c.jogador)}`,
      formatarValor: c => `${c.amarelos}&#129000;${c.vermelhos ? ` ${c.vermelhos}&#128997;` : ''}`,
    }
  );

  graficoBarras(
    document.getElementById('grafico-jornadas'),
    dados.golos_por_jornada.map(j => ({ ...j, valor: j.golos })),
    { formatarLabel: j => `Jornada ${j.jornada}`, formatarValor: j => j.golos }
  );

  graficoBarras(
    document.getElementById('grafico-posicao'),
    dados.golos_por_posicao.map(p => ({ ...p, valor: p.golos })),
    { formatarLabel: p => esc(p.grupo), formatarValor: p => p.golos }
  );
}

// ------------------------------------------------------------------
// Navegação entre painéis
// ------------------------------------------------------------------

const CARREGADORES = {
  classificacao: async () => renderClassificacao(await pedirJSON('/api/classificacao')),
  jornadas: async () => renderJornadas(await pedirJSON('/api/jornadas')),
  jogadores: carregarJogadores,
  clubes: carregarClubes,
  estatisticas: carregarEstatisticas,
};

let painelAtivo = 'classificacao';

async function carregarPainel(nome) {
  esconderErro();
  try {
    await CARREGADORES[nome]();
  } catch (e) {
    mostrarErro(e.message);
  }
}

function mostrarPainel(nome) {
  painelAtivo = nome;
  document.querySelectorAll('.painel').forEach(p => { p.hidden = p.dataset.painel !== nome; });
  document.querySelectorAll('.menu-item').forEach(b => b.classList.toggle('ativo', b.dataset.painel === nome));
  carregarPainel(nome);
}

document.querySelectorAll('.menu-item').forEach(btn => {
  btn.addEventListener('click', () => mostrarPainel(btn.dataset.painel));
});

document.getElementById('btn-gerar-calendario').addEventListener('click', gerarCalendario);
document.getElementById('btn-reiniciar').addEventListener('click', reiniciarEpoca);

mostrarPainel('classificacao');
