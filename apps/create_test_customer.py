from apps import db
from apps.authentication.models import Customer
from apps import create_app

app = create_app()
app.app_context().push()

cliente = Customer(
    nome_razao_social='Empresa ABC Ltda',
    nif='123456789',
    tipo_cliente='coletiva',
    rua='Avenida da República',
    numero='123',
    complemento='4º Andar',
    codigo_postal='1050-007',
    localidade='Lisboa',
    concelho='Lisboa',
    distrito='Lisboa',
    telefone='213456789',
    email='contato@empresaabc.pt',
    pessoa_contato='João Silva',
    razao_social='Empresa ABC, Limitada',
    cae='12345',
    nipc='987654321',
    iban='PT50123456789012345678901',
    metodo_pagamento='transferencia',
    condicoes_pagamento='30dias',
    observacoes='Cliente importante do setor tecnológico'
)

try:
    db.session.add(cliente)
    db.session.commit()
    print('Cliente criado com sucesso!')
except Exception as e:
    db.session.rollback()
    print(f'Erro ao criar cliente: {str(e)}') 