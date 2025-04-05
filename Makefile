# Makefile para Hub MConfea

# Variáveis
COMPOSE = docker-compose -f docker-compose.dev.yml

# Comandos
up:
	$(COMPOSE) down
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) exec appseed-app flask db init
	$(COMPOSE) exec appseed-app flask db migrate -m "Initial migration"
	$(COMPOSE) exec appseed-app flask db upgrade

logs:
	$(COMPOSE) logs -f

prune:
	docker system prune -f

# Uso:
# make up       -> Derruba e sobe tudo com build
# make migrate  -> Faz as migrações
# make down     -> Derruba os containers
# make logs     -> Mostra os logs em tempo real
# make prune    -> Limpa imagens e containers antigos