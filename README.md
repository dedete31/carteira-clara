# Carteira Clara

MVP de acompanhamento de carteiras por cliente, em português, como PWA (aplicativo web instalável). Não exige build nem servidor para a versão local: sirva os arquivos por HTTP/HTTPS para instalar no celular.

## Escopo do MVP

- Cadastro de vários clientes, cada um com carteira independente.
- Posições com ticker, quantidade e custo médio; edição substitui a posição total atual.
- Exclusão de uma posição específica, com confirmação antes de remover.
- Cálculo de custo investido, valor estimado de mercado e retorno simples sobre custo médio.
- Gráfico de evolução do valor de mercado e do custo investido por carteira, com pontos diários registrados no dispositivo.
- Atualização automática diária pelo arquivo COTAHIST da B3; um job baixa e processa o ZIP fora do aparelho e mantém um feed compacto de fechamentos.
- Persistência local no navegador e exportação de cópia JSON.
- Layout responsivo e manifest/service worker para instalação e acesso ao app offline (sem cotações offline).

## Rodar

Abra esta pasta em um servidor estático local ou publique por HTTPS. Em celulares, use “Adicionar à tela inicial” no menu do navegador. O service worker não funciona em `file://`.

## Arquitetura escolhida

PWA responsiva com HTML/CSS/JavaScript sem dependências externas de runtime. O armazenamento de clientes e posições usa `localStorage`. Um workflow do GitHub Actions roda em horário agendado após o pregão, baixa o COTAHIST diário para o runner, descompacta e percorre o TXT linha por linha com memória limitada, e publica só um mapa JSON compacto de ticker, fechamento e data. A PWA busca o feed ao abrir, quando volta ao primeiro plano e a cada seis horas enquanto fica aberta. O aparelho nunca baixa o ZIP bruto nem os arquivos anuais.

## Dados, segurança e limites

Os dados de clientes e posições permanecem no navegador deste dispositivo; não são enviados ao workflow nem publicados. O feed público contém apenas preços de mercado do COTAHIST. Não há autenticação, criptografia própria, sincronização de carteiras ou controle de acesso entre usuários. O bloqueio de tela do aparelho e a segurança do navegador são essenciais. Para atender uso profissional com múltiplos usuários/dispositivos, a próxima etapa é backend Supabase (Auth + PostgreSQL) com `user_id` e políticas Row Level Security em clientes, carteiras e posições. Backup e trilha de auditoria também devem entrar antes do uso com dados reais de clientes.

Rentabilidade é uma aproximação: não inclui impostos, corretagem, proventos, eventos corporativos ou fluxos de caixa e não equivale ao retorno ponderado pelo tempo. O COTAHIST contém fechamentos por pregão, não cotações intradiárias; o feed é atualizado uma vez por dia útil após a publicação do arquivo pela B3. Em fins de semana e feriados, mantém-se o último pregão disponível. O layout tem registros fixos de 245 bytes. A B3 esclarece que dados históricos e de fim de dia D-1 têm regime diferente de market data intraday; verifique os termos aplicáveis ao uso e à redistribuição. Cotações não são recomendação de investimento.

O gráfico de evolução começa a partir dos fechamentos consultados depois desta versão. Ele não reconstrói períodos anteriores e não guarda pontos dos pregões em que o aplicativo não foi aberto para consultar o feed. O histórico do gráfico também permanece no armazenamento local do navegador.

## Ativar a automação e publicar o app

1. Coloque o projeto em um repositório GitHub e deixe o GitHub Actions habilitado.
2. Em **Settings → Pages**, escolha **GitHub Actions** como fonte de publicação.
3. O workflow `.github/workflows/cotahist-daily.yml` atualiza `data/quotes.json` de segunda a sexta por volta de 22h (horário de Brasília) e publica o app. Também pode ser executado manualmente pela aba Actions.

O repositório precisa aceitar os commits automáticos do feed. A publicação em GitHub Pages torna o app e o arquivo público; as carteiras continuam apenas no armazenamento local do navegador. Se o código do app também precisar ficar privado, publique os arquivos num host privado compatível e ajuste apenas a etapa de publicação do workflow.

## Fontes consultadas (06/10/2026)

- [Cotações históricas B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/): página oficial e descrição do produto histórico.
- [Layout oficial COTAHIST](https://www.b3.com.br/data/files/C8/F3/08/B4/297BE410F816C9E492D828A8/SeriesHistoricas_Layout.pdf): registros de 245 bytes e posições dos campos.
- [FAQ Market Data B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/distribuidores/perguntas-frequentes/): direitos/licenças para distribuição de dados B3 em tempo real e com atraso; dados de fim de dia têm regime distinto.
