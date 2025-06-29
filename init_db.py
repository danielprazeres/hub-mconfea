from apps import create_app, db
from apps.authentication.models import Users, Customer, ServiceItem
from apps.config import config_dict

app = create_app(config_dict['Debug'])

with app.app_context():
    # Criar usuário admin
    if not Users.query.filter_by(username='admin').first():
        admin = Users(
            username='admin',
            email='admin@mconfea.com',
            password='admin123'  # Senha: admin123
        )
        db.session.add(admin)
    
    # Criar cliente fictício
    if not Customer.query.filter_by(nif='123456789').first():
        cliente = Customer(
            nome_razao_social='Empresa Teste, Lda',
            nif='123456789',
            tipo_cliente='coletiva',
            rua='Rua Principal',
            numero='123',
            complemento='Sala 4',
            codigo_postal='1000-000',
            localidade='Lisboa',
            concelho='Lisboa',
            distrito='Lisboa',
            pais='Portugal',
            telefone='912345678',
            email='contato@empresateste.pt',
            pessoa_contato='João Silva',
            razao_social='Empresa Teste, Lda',
            cae='12345',
            nipc='123456789',
            iban='PT50123456789012345678901',
            metodo_pagamento='Transferência',
            condicoes_pagamento='30 dias',
            observacoes='Cliente fictício para testes'
        )
        db.session.add(cliente)
    
    # Criar serviços padrão
    servicos = [
        {
            'codigo': '999',
            'descricao': 'Mão de Obra - Balanço de Potência em quadro elétrico trifásico',
            'tipo': 'Mão de Obra',
            'preco_padrao': 200.00,
            'iva_padrao': 23.00
        },
        {
            'codigo': '0003',
            'descricao': 'Material - Detector de movimento 160° GARZA',
            'tipo': 'Material',
            'preco_padrao': 9.59,
            'iva_padrao': 23.00
        }
    ]
    
    for servico in servicos:
        if not ServiceItem.query.filter_by(codigo=servico['codigo']).first():
            item = ServiceItem(**servico)
            db.session.add(item)
    
    # Commit das alterações
    try:
        db.session.commit()
        print("Banco de dados inicializado com sucesso!")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao inicializar o banco de dados: {str(e)}") 