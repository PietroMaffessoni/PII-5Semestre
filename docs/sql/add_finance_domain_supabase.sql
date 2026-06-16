-- Migracao incremental para adicionar dados financeiros/folha ao Supabase.
-- Nao recria nem limpa os dominios existentes; apenas faz upsert do dicionario
-- financeiro e repopula a tabela ficticia agregada zhr_folha.

BEGIN;

INSERT INTO sap_domains (name, chart_recommendation)
VALUES ('financeiro', 'grafico de linhas ou colunas por mes e departamento')
ON CONFLICT (name) DO UPDATE
SET chart_recommendation = EXCLUDED.chart_recommendation;

INSERT INTO sap_domain_terms (domain_id, term)
SELECT d.id, v.term
FROM sap_domains d
JOIN (
    VALUES
        ('financeiro', 'financeiro'),
        ('financeiro', 'folha'),
        ('financeiro', 'folha de pagamento'),
        ('financeiro', 'salario'),
        ('financeiro', 'salarios'),
        ('financeiro', 'salario medio'),
        ('financeiro', 'media salarial'),
        ('financeiro', 'rendimento'),
        ('financeiro', 'rendimentos'),
        ('financeiro', 'beneficio'),
        ('financeiro', 'beneficios'),
        ('financeiro', 'encargo'),
        ('financeiro', 'encargos'),
        ('financeiro', 'desconto'),
        ('financeiro', 'descontos'),
        ('financeiro', 'custo de pessoal'),
        ('financeiro', 'departamento'),
        ('financeiro', 'centro de custo'),
        ('financeiro', 'cargo'),
        ('financeiro', 'remuneracao'),
        ('financeiro', 'recursos humanos'),
        ('financeiro', 'rh'),
        ('financeiro', 'payroll')
) AS v(domain_name, term)
    ON d.name = v.domain_name
ON CONFLICT (domain_id, term) DO NOTHING;

INSERT INTO sap_tables (name, module, domain_id, description)
SELECT 'ZHR_FOLHA', 'FI-HR', d.id, 'Resumo mensal agregado da folha de pagamento por departamento e cargo'
FROM sap_domains d
WHERE d.name = 'financeiro'
ON CONFLICT (name) DO UPDATE
SET
    module = EXCLUDED.module,
    domain_id = EXCLUDED.domain_id,
    description = EXCLUDED.description;

INSERT INTO sap_table_terms (table_id, term)
SELECT t.id, v.term
FROM sap_tables t
JOIN (
    VALUES
        ('ZHR_FOLHA', 'folha de pagamento'),
        ('ZHR_FOLHA', 'salario'),
        ('ZHR_FOLHA', 'salario bruto'),
        ('ZHR_FOLHA', 'salario liquido'),
        ('ZHR_FOLHA', 'salario medio'),
        ('ZHR_FOLHA', 'media salarial'),
        ('ZHR_FOLHA', 'rendimento'),
        ('ZHR_FOLHA', 'beneficio'),
        ('ZHR_FOLHA', 'encargo'),
        ('ZHR_FOLHA', 'desconto'),
        ('ZHR_FOLHA', 'custo total da folha'),
        ('ZHR_FOLHA', 'departamento'),
        ('ZHR_FOLHA', 'centro de custo'),
        ('ZHR_FOLHA', 'cargo'),
        ('ZHR_FOLHA', 'remuneracao'),
        ('ZHR_FOLHA', 'recursos humanos'),
        ('ZHR_FOLHA', 'rh')
) AS v(table_name, term)
    ON t.name = v.table_name
ON CONFLICT (table_id, term) DO NOTHING;

INSERT INTO sap_table_join_keys (table_id, join_key)
SELECT t.id, v.join_key
FROM sap_tables t
JOIN (
    VALUES
        ('ZHR_FOLHA', 'KOSTL'),
        ('ZHR_FOLHA', 'DEPARTAMENTO'),
        ('ZHR_FOLHA', 'CARGO')
) AS v(table_name, join_key)
    ON t.name = v.table_name
ON CONFLICT (table_id, join_key) DO NOTHING;

INSERT INTO sap_fields (table_id, field_name, label, data_type, description)
SELECT t.id, v.field_name, v.label, v.data_type, v.description
FROM sap_tables t
JOIN (
    VALUES
        ('ZHR_FOLHA', 'DOCFOLHA', 'documento_folha', 'text', 'Identificador do resumo mensal da folha'),
        ('ZHR_FOLHA', 'COMPETENCIA', 'mes', 'date', 'Competencia mensal da folha'),
        ('ZHR_FOLHA', 'KOSTL', 'centro_custo', 'text', 'Centro de custo responsavel pela despesa de pessoal'),
        ('ZHR_FOLHA', 'DEPARTAMENTO', 'departamento', 'text', 'Departamento consolidado da folha'),
        ('ZHR_FOLHA', 'CARGO', 'cargo', 'text', 'Cargo ou familia de cargos'),
        ('ZHR_FOLHA', 'QTD_FUNC', 'quantidade_funcionarios', 'number', 'Quantidade de funcionarios no grupo'),
        ('ZHR_FOLHA', 'SAL_BASE', 'salario_base', 'number', 'Soma do salario base'),
        ('ZHR_FOLHA', 'REND_TOTAL', 'rendimento_total', 'number', 'Soma dos rendimentos brutos'),
        ('ZHR_FOLHA', 'BENEFICIOS', 'beneficios', 'number', 'Valor total de beneficios'),
        ('ZHR_FOLHA', 'DESCONTOS', 'descontos', 'number', 'Valor total de descontos'),
        ('ZHR_FOLHA', 'ENCARGOS', 'encargos', 'number', 'Encargos patronais estimados'),
        ('ZHR_FOLHA', 'SAL_LIQUIDO', 'salario_liquido', 'number', 'Valor liquido pago aos funcionarios'),
        ('ZHR_FOLHA', 'CUSTO_TOTAL', 'custo_total_folha', 'number', 'Custo total da folha incluindo rendimentos, beneficios e encargos')
) AS v(table_name, field_name, label, data_type, description)
    ON t.name = v.table_name
ON CONFLICT (table_id, field_name) DO UPDATE
SET
    label = EXCLUDED.label,
    data_type = EXCLUDED.data_type,
    description = EXCLUDED.description;

CREATE TABLE IF NOT EXISTS zhr_folha (
    docfolha TEXT PRIMARY KEY,
    competencia DATE NOT NULL,
    kostl TEXT NOT NULL,
    departamento TEXT NOT NULL,
    cargo TEXT NOT NULL,
    qtd_func NUMERIC(14, 2) NOT NULL,
    sal_base NUMERIC(14, 2) NOT NULL,
    rend_total NUMERIC(14, 2) NOT NULL,
    beneficios NUMERIC(14, 2) NOT NULL,
    descontos NUMERIC(14, 2) NOT NULL,
    encargos NUMERIC(14, 2) NOT NULL,
    sal_liquido NUMERIC(14, 2) NOT NULL,
    custo_total NUMERIC(14, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_zhr_folha_competencia_departamento
    ON zhr_folha (competencia, departamento);

CREATE INDEX IF NOT EXISTS idx_zhr_folha_kostl_cargo
    ON zhr_folha (kostl, cargo);

TRUNCATE TABLE zhr_folha;

DO $$
DECLARE
    history_months INTEGER := 36;
    start_month DATE := (DATE_TRUNC('month', CURRENT_DATE) - MAKE_INTERVAL(months => history_months))::date;
    departments TEXT[] := ARRAY['OPERACOES', 'COMERCIAL', 'FINANCEIRO', 'TECNOLOGIA', 'LOGISTICA', 'RH'];
    cost_centers TEXT[] := ARRAY['CC-100', 'CC-200', 'CC-300', 'CC-400', 'CC-500', 'CC-600'];
    roles TEXT[] := ARRAY['ANALISTA', 'COORDENADOR', 'ESPECIALISTA', 'GERENTE'];
    role_salary_factor NUMERIC[] := ARRAY[1.00, 1.42, 1.68, 2.35];
    seasonality NUMERIC[] := ARRAY[1.16, 0.94, 1.01, 1.08, 1.04, 1.12, 0.96, 0.91, 1.02, 1.07, 1.18, 1.28];
    payroll_seq BIGINT := 7000000;
    month_offset INTEGER;
    month_start DATE;
    month_factor NUMERIC;
    dept_idx INTEGER;
    role_idx INTEGER;
    headcount NUMERIC;
    salary_base NUMERIC;
    earnings_total NUMERIC;
    benefits_amount NUMERIC;
    discounts_amount NUMERIC;
    charges_amount NUMERIC;
    net_salary NUMERIC;
    total_cost NUMERIC;
BEGIN
    FOR month_offset IN 0..history_months - 1 LOOP
        month_start := (start_month + MAKE_INTERVAL(months => month_offset))::date;
        month_factor := seasonality[EXTRACT(MONTH FROM month_start)::INTEGER];

        FOR dept_idx IN 1..array_length(departments, 1) LOOP
            FOR role_idx IN 1..array_length(roles, 1) LOOP
                payroll_seq := payroll_seq + 1;
                headcount := 4 + ((month_offset + dept_idx * 2 + role_idx) % 13);
                salary_base := ROUND(
                    (
                        headcount
                        * (3200 + dept_idx * 420 + role_idx * 760)
                        * role_salary_factor[role_idx]
                        * (1 + ((month_offset % 12) * 0.006))
                    )::NUMERIC,
                    2
                );
                earnings_total := ROUND((salary_base * (1.08 + ((dept_idx + role_idx) % 4) * 0.025))::NUMERIC, 2);
                benefits_amount := ROUND((headcount * (620 + dept_idx * 35 + role_idx * 28) * month_factor)::NUMERIC, 2);
                discounts_amount := ROUND((earnings_total * (0.075 + (role_idx % 3) * 0.008))::NUMERIC, 2);
                charges_amount := ROUND((earnings_total * (0.265 + (dept_idx % 2) * 0.015))::NUMERIC, 2);
                net_salary := ROUND((earnings_total - discounts_amount)::NUMERIC, 2);
                total_cost := ROUND((earnings_total + benefits_amount + charges_amount)::NUMERIC, 2);

                INSERT INTO zhr_folha (
                    docfolha,
                    competencia,
                    kostl,
                    departamento,
                    cargo,
                    qtd_func,
                    sal_base,
                    rend_total,
                    beneficios,
                    descontos,
                    encargos,
                    sal_liquido,
                    custo_total
                )
                VALUES (
                    payroll_seq::TEXT,
                    month_start,
                    cost_centers[dept_idx],
                    departments[dept_idx],
                    roles[role_idx],
                    headcount,
                    salary_base,
                    earnings_total,
                    benefits_amount,
                    discounts_amount,
                    charges_amount,
                    net_salary,
                    total_cost
                );
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

INSERT INTO sap_dictionary_embeddings (
    source_key,
    source_type,
    table_name,
    field_name,
    module,
    domain_name,
    description,
    content_text,
    embedding
)
SELECT
    CONCAT('table:', t.name),
    'table',
    t.name,
    NULL,
    t.module,
    d.name,
    t.description,
    CONCAT(
        'Tabela SAP ', t.name,
        ' do modulo ', t.module,
        '. Dominio: ', d.name,
        '. Descricao: ', t.description
    ),
    NULL
FROM sap_tables t
JOIN sap_domains d ON d.id = t.domain_id
WHERE t.name = 'ZHR_FOLHA'
ON CONFLICT (source_key) DO UPDATE
SET
    source_type = EXCLUDED.source_type,
    table_name = EXCLUDED.table_name,
    field_name = EXCLUDED.field_name,
    module = EXCLUDED.module,
    domain_name = EXCLUDED.domain_name,
    description = EXCLUDED.description,
    content_text = EXCLUDED.content_text,
    embedding = CASE
        WHEN sap_dictionary_embeddings.content_text IS DISTINCT FROM EXCLUDED.content_text
            THEN NULL
        ELSE sap_dictionary_embeddings.embedding
    END;

INSERT INTO sap_dictionary_embeddings (
    source_key,
    source_type,
    table_name,
    field_name,
    module,
    domain_name,
    description,
    content_text,
    embedding
)
SELECT
    CONCAT('field:', t.name, '.', f.field_name),
    'field',
    t.name,
    f.field_name,
    t.module,
    d.name,
    f.description,
    CONCAT(
        'Campo ', t.name, '.', f.field_name,
        ' com label ', f.label,
        '. Tipo: ', f.data_type,
        '. Descricao: ', f.description,
        '. Dominio: ', d.name
    ),
    NULL
FROM sap_fields f
JOIN sap_tables t ON t.id = f.table_id
JOIN sap_domains d ON d.id = t.domain_id
WHERE t.name = 'ZHR_FOLHA'
ON CONFLICT (source_key) DO UPDATE
SET
    source_type = EXCLUDED.source_type,
    table_name = EXCLUDED.table_name,
    field_name = EXCLUDED.field_name,
    module = EXCLUDED.module,
    domain_name = EXCLUDED.domain_name,
    description = EXCLUDED.description,
    content_text = EXCLUDED.content_text,
    embedding = CASE
        WHEN sap_dictionary_embeddings.content_text IS DISTINCT FROM EXCLUDED.content_text
            THEN NULL
        ELSE sap_dictionary_embeddings.embedding
    END;

COMMIT;
