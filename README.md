
# Bot de Mangás para Discord

Um bot para compartilhar e coletar mangás aleatórios no Discord. Este bot utiliza a API Jikan para acessar dados do MyAnimeList.

## Funcionalidades

O bot oferece os seguintes comandos:

- `/rl` - Recebe um mangá aleatório **SFW (Safe for Work)** que pode ser pego reagindo com qualquer emoji
- `/meusmangas` - Vê a lista de mangás que você já pegou
- `/ranking` - Veja o ranking de quem pegou mais mangás no servidor
- `/ajuda` - Exibe informações detalhadas sobre os comandos do bot
- `/estatisticas` - Mostra estatísticas de uso do bot
- `/status` - Exibe status do bot e sistema keep-alive

### Filtro de Conteúdo SFW

O bot implementa um sistema duplo de filtragem para garantir que apenas conteúdo apropriado seja exibido:

1. **Filtro da API**: Utiliza o parâmetro `sfw=true` da API Jikan
2. **Filtro do Cliente**: Validação adicional que verifica gêneros, demografias e ratings para filtrar conteúdo NSFW

### Características Avançadas

- **Sistema de Cache**: Reduz o número de requisições à API e melhora o tempo de resposta
- **Limites de Taxa**: Evita abuso do bot com limites de mangás por período
- **Banco de Dados Assíncrono**: Utiliza PostgreSQL com asyncpg para operações de banco de dados sem bloquear o bot
- **Métricas de Desempenho**: Acompanha estatísticas de uso, tempo de resposta e erros
- **Sistema Keep-Alive**: Mantém o bot online em serviços gratuitos como Render.com
- **Testes Unitários**: Verificação automatizada de funcionalidades principais

## Requisitos

- Python 3.11 ou superior
- Token de Bot do Discord
- Banco de dados PostgreSQL
- Bibliotecas:
  - discord.py (>=2.0.0)
  - python-dotenv (>=1.0.0)
  - aiohttp (>=3.8.0)
  - asyncpg (>=0.28.0)
  - typing_extensions (>=4.0.0)

## Instalação

### Deploy no Render.com (Recomendado para hospedagem gratuita)

O bot inclui um sistema keep-alive otimizado para funcionar no Render.com:

1. Faça fork deste repositório no GitHub
2. Crie uma conta no [Render.com](https://render.com)
3. Crie um novo "Web Service" conectado ao seu repositório
4. Configure as variáveis de ambiente:
   - `DISCORD_TOKEN`: Seu token do bot Discord
   - `DATABASE_URL`: Será fornecido automaticamente pelo Render
5. O Render fará o deploy automaticamente

Para instruções detalhadas, consulte [RENDER_SETUP.md](RENDER_SETUP.md).

### Usando Docker (Recomendado)

1. Clone este repositório
2. Crie um arquivo `.env` na raiz do projeto com seu token:

   ```env
   DISCORD_TOKEN="seu_token_aqui"
   ```

3. Construa e execute a imagem Docker:

   ```powershell
   docker build -t discord-manga-bot .
   docker run -d --name manga-bot -v ./data:/app/data discord-manga-bot
   ```

### Instalação manual

1. Clone este repositório
2. Instale as dependências:

   ```powershell
   pip install -r requirements.txt
   ```

3. Crie um arquivo `.env` na raiz do projeto com seu token
4. Execute o bot:

   ```powershell
   python main.py
   ```

## Uso

O bot responde aos seguintes comandos de barra (slash commands):

- `/rl` - Obtenha um mangá aleatório para colecionar
- `/meusmangas` - Veja sua coleção de mangás pegos
- `/ranking` - Veja o ranking dos usuários com mais mangás
- `/ajuda` - Mostra informações de ajuda detalhadas
- `/estatisticas` - Exibe estatísticas de uso do bot
- `/status` - Mostra status do bot e sistema keep-alive

## Sistema Keep-Alive

O bot inclui um sistema keep-alive integrado que:

- **Cria um servidor HTTP interno** para receber requisições
- **Faz auto-ping a cada 13 minutos** para evitar hibernação em serviços gratuitos
- **Fornece endpoints de monitoramento**:
  - `/` - Página principal com informações do bot
  - `/ping` - Endpoint para keep-alive
  - `/health` - Health check para monitoramento
  - `/stats` - Estatísticas do bot em formato JSON

Este sistema é especialmente útil para deployments no Render.com, Heroku e outros serviços que hibernam aplicações após períodos de inatividade.

## Testes

Para executar os testes unitários:

```powershell
python run_tests.py
```

## Configurações Avançadas

Você pode customizar o comportamento do bot através das seguintes variáveis de ambiente:

```env
DISCORD_TOKEN=seu_token_aqui
DATABASE_URL=postgresql://usuario:senha@host:porta/database?sslmode=require
JIKAN_API_BASE=url_alternativa_da_api
```

## Arquitetura

O projeto segue uma arquitetura modular:

- `api/`: Interfaces com APIs externas (Jikan/MyAnimeList)
- `bot/`: Lógica principal do cliente Discord e comandos
- `database/`: Gerenciamento de dados e persistência
- `utils/`: Ferramentas auxiliares, logging e métricas
- `views/`: Componentes da interface do Discord (botões, paginação)
- `tests/`: Testes unitários

## Como usar

### Sistema de Mangás

1. Use o comando `/rl` para receber um mangá aleatório
2. Reaja ao mangá com qualquer emoji para pegá-lo
3. Cada mangá só pode ser pego por um usuário
4. Use `/meusmangas` para ver sua coleção
5. Confira o `/ranking` para ver quem tem mais mangás

## Observações

- O arquivo `.env` com seu token não deve ser compartilhado ou commitado
