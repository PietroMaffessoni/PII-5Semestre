export const projectCards = {
  problema: {
    title: 'Problema',
    text: 'Gestores e analistas precisam transformar perguntas de negocio em extracoes SAP, mas nem sempre conhecem a estrutura tecnica das tabelas e dependem do time especialista para avancar.',
  },
  impacto: {
    title: 'Impacto do problema',
    items: [
      'Atrasos na criacao de dashboards estrategicos por falta de scripts prontos.',
      'Baixa autonomia de usuarios de negocio na exploracao de dados.',
      'Sobrecarga da equipe tecnica com demandas repetitivas de extracao.',
    ],
  },
  publico: {
    title: 'Publico',
    items: [
      'Time de Analytics e comunidade Power BI.',
      'Usuarios de negocio que precisam consultar dados SAP com mais autonomia.',
    ],
  },
  estrategia: {
    title: 'Estrategia de solucao',
    items: [
      'Interpretar a intencao do usuario em linguagem natural.',
      'Mapear tabelas e campos SAP relevantes usando RAG sobre dicionarios tecnicos.',
      'Gerar um rascunho de SQL pronto para validação e uso no Power BI.',
    ],
  },
  valor: {
    title: 'Valor capturado',
    items: [
      'Reducao de horas tecnicas dedicadas a extracao e transformacao.',
      'Menor tempo de alinhamento entre negocio e time tecnico.',
      'Padronizacao da criacao de scripts e testes.',
    ],
  },
  riscos: {
    title: 'Riscos',
    items: [
      'Geracao de logica incorreta ou incompleta.',
      'Acesso indevido a dados sensiveis sem governanca adequada.',
      'Dependencia de um dicionario SAP desatualizado.',
    ],
  },
  sinergia: {
    title: 'Sinergia com outras acoes',
    text: 'A estrutura permite reaproveitar uma base de RAG corporativa, conectores de dados SAP e mecanismos de automacao para catalogacao e governanca.',
  },
}
