-- ============================================================
-- PROJETO FINAL — Base de Dados de um Campeonato de Futebol
-- Script de criação da base de dados (modelo lógico -> PostgreSQL)
-- ============================================================

-- Opcional: criar a base de dados (correr fora de uma transação,
-- ligado a outra base de dados, ex: postgres)
-- CREATE DATABASE campeonato_futebol;

-- ============================================================
-- 1. ESTADIO
-- ============================================================
CREATE TABLE estadio (
    id_estadio   SERIAL PRIMARY KEY,
    nome         VARCHAR(100) NOT NULL,
    cidade       VARCHAR(100) NOT NULL,
    capacidade   INTEGER NOT NULL CHECK (capacidade > 0)
);

-- ============================================================
-- 2. CLUBE
-- ============================================================
CREATE TABLE clube (
    id_clube       SERIAL PRIMARY KEY,
    nome           VARCHAR(100) NOT NULL UNIQUE,
    cidade         VARCHAR(100) NOT NULL,
    ano_fundacao   INTEGER NOT NULL CHECK (ano_fundacao >= 1850 AND ano_fundacao <= EXTRACT(YEAR FROM CURRENT_DATE)),
    id_estadio     INTEGER NOT NULL REFERENCES estadio(id_estadio),
    logo_url       VARCHAR(255)
);

-- ============================================================
-- 3. JOGADOR
-- ============================================================
CREATE TABLE jogador (
    id_jogador        SERIAL PRIMARY KEY,
    nome              VARCHAR(100) NOT NULL,
    data_nascimento   DATE NOT NULL,
    nacionalidade     VARCHAR(60) NOT NULL,
    posicao           VARCHAR(30) NOT NULL,
    numero_camisola   INTEGER NOT NULL CHECK (numero_camisola > 0),
    id_clube          INTEGER NOT NULL REFERENCES clube(id_clube),

    -- Regra adicional: dois jogadores do mesmo clube não podem
    -- partilhar o mesmo número de camisola
    CONSTRAINT uq_numero_por_clube UNIQUE (id_clube, numero_camisola)
);

-- ============================================================
-- 4. TREINADOR
-- ============================================================
CREATE TABLE treinador (
    id_treinador   SERIAL PRIMARY KEY,
    nome           VARCHAR(100) NOT NULL,
    id_clube       INTEGER NOT NULL REFERENCES clube(id_clube)
);

-- ============================================================
-- 5. JORNADA
-- ============================================================
CREATE TABLE jornada (
    id_jornada   SERIAL PRIMARY KEY,
    numero       INTEGER NOT NULL,
    epoca        VARCHAR(20) NOT NULL,

    -- Não pode haver duas jornadas iguais na mesma época
    CONSTRAINT uq_numero_por_epoca UNIQUE (epoca, numero)
);

-- ============================================================
-- 6. JOGO
-- ============================================================
CREATE TABLE jogo (
    id_jogo                SERIAL PRIMARY KEY,
    id_jornada             INTEGER NOT NULL REFERENCES jornada(id_jornada),
    data_jogo              DATE NOT NULL,
    id_equipa_casa         INTEGER NOT NULL REFERENCES clube(id_clube),
    id_equipa_visitante    INTEGER NOT NULL REFERENCES clube(id_clube),
    id_estadio             INTEGER NOT NULL REFERENCES estadio(id_estadio),
    golos_casa             INTEGER NOT NULL DEFAULT 0 CHECK (golos_casa >= 0),
    golos_visitante        INTEGER NOT NULL DEFAULT 0 CHECK (golos_visitante >= 0),

    -- Regra de negócio 1: uma equipa não pode jogar contra si própria
    CONSTRAINT chk_equipas_diferentes CHECK (id_equipa_casa <> id_equipa_visitante)
);

-- ============================================================
-- 7. GOLO
-- ============================================================
CREATE TABLE golo (
    id_golo      SERIAL PRIMARY KEY,
    id_jogador   INTEGER NOT NULL REFERENCES jogador(id_jogador),
    id_jogo      INTEGER NOT NULL REFERENCES jogo(id_jogo),
    minuto       INTEGER NOT NULL CHECK (minuto >= 0 AND minuto <= 130)
);

-- ============================================================
-- 8. CARTAO
-- ============================================================
CREATE TABLE cartao (
    id_cartao      SERIAL PRIMARY KEY,
    id_jogador     INTEGER NOT NULL REFERENCES jogador(id_jogador),
    id_jogo        INTEGER NOT NULL REFERENCES jogo(id_jogo),
    minuto         INTEGER NOT NULL CHECK (minuto >= 0 AND minuto <= 130),
    tipo_cartao    VARCHAR(10) NOT NULL CHECK (tipo_cartao IN ('Amarelo', 'Vermelho'))
);

-- ============================================================
-- Índices adicionais para consultas frequentes
-- ============================================================
CREATE INDEX idx_jogo_jornada ON jogo(id_jornada);
CREATE INDEX idx_jogador_clube ON jogador(id_clube);
CREATE INDEX idx_golo_jogador ON golo(id_jogador);
CREATE INDEX idx_golo_jogo ON golo(id_jogo);
CREATE INDEX idx_cartao_jogo ON cartao(id_jogo);
