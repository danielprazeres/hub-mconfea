# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin

from sqlalchemy.orm import relationship
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin

from apps import db, login_manager

from apps.authentication.util import hash_pass

class Users(db.Model, UserMixin):

    __tablename__ = 'Users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True)
    email         = db.Column(db.String(64), unique=True)
    password      = db.Column(db.LargeBinary)
    profile_photo = db.Column(db.String(255), default='img/default-avatar.png')
    oauth_github  = db.Column(db.String(100), nullable=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("Users.id", ondelete="cascade"), nullable=False)
    user = db.relationship(Users)

class Customer(db.Model):
    __tablename__ = 'Customers'

    id = db.Column(db.Integer, primary_key=True)
    
    # Identificação Fiscal
    nome_razao_social = db.Column(db.String(200), nullable=False)
    nif = db.Column(db.String(20), unique=True, nullable=False)
    tipo_cliente = db.Column(db.String(20), nullable=False)  # Pessoa Singular / Pessoa Coletiva
    
    # Endereço Fiscal / Morada de Faturação
    morada = db.Column(db.String(200))  # Endereço completo
    rua = db.Column(db.String(200))
    numero = db.Column(db.String(20))
    lote = db.Column(db.String(20))  # Campo solicitado
    complemento = db.Column(db.String(100))
    codigo_postal = db.Column(db.String(20))
    cidade = db.Column(db.String(100))  # Renomeado de localidade
    localidade = db.Column(db.String(100))  # Mantido para compatibilidade
    concelho = db.Column(db.String(100))
    distrito = db.Column(db.String(100))
    pais = db.Column(db.String(100))
    
    # Contato
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    pessoa_contato = db.Column(db.String(100))
    
    # Dados Empresariais
    razao_social = db.Column(db.String(200))
    cae = db.Column(db.String(20))
    nipc = db.Column(db.String(20))
    
    # Faturamento/Pagamento
    iban = db.Column(db.String(50))
    metodo_pagamento = db.Column(db.String(50))
    condicoes_pagamento = db.Column(db.String(50))
    
    # Outros
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f'<Customer {self.nome_razao_social}>'

class ServiceItem(db.Model):
    __tablename__ = 'service_items'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10))  # Exemplo: 999, 0003
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50))  # Mão de Obra, Material, etc
    preco_padrao = db.Column(db.Float)
    iva_padrao = db.Column(db.Float, default=23.00)
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<ServiceItem {self.descricao}>'

class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True)  # FT SERIE1/230
    data_doc = db.Column(db.Date, nullable=False)
    data_venc = db.Column(db.Date)
    moeda = db.Column(db.String(3), default='EUR')
    cambio = db.Column(db.Float, default=1.0)
    cod_entidade = db.Column(db.String(10))
    cliente_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    desc_global = db.Column(db.Float, default=0.0)
    desc_valor = db.Column(db.Float, default=0.0)
    v_num = db.Column(db.String(50))
    prazo_pag = db.Column(db.String(50))
    
    # Informações de entrega
    local_carga = db.Column(db.String(200))
    data_carga = db.Column(db.DateTime)
    hora_carga = db.Column(db.String(8))
    local_descarga = db.Column(db.String(200))
    data_descarga = db.Column(db.DateTime)
    hora_descarga = db.Column(db.String(8))
    veiculo = db.Column(db.String(50))
    expedicao = db.Column(db.String(50))
    
    # Relacionamentos
    cliente = db.relationship('Customer', backref='budgets')
    items = db.relationship('BudgetItem', backref='budget', cascade='all, delete-orphan')
    
    # Campos calculados
    total_mercadorias = db.Column(db.Float, default=0.0)
    total_iva = db.Column(db.Float, default=0.0)
    total_desconto = db.Column(db.Float, default=0.0)
    valor_total = db.Column(db.Float, default=0.0)
    
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.String(20), default='rascunho')  # rascunho, aprovado, rejeitado, faturado
    
    def __repr__(self):
        return f'<Budget {self.numero}>'
    
    @property
    def subtotal(self):
        return sum(item.total for item in self.items)
        
    @property
    def valor_desc_global(self):
        return self.subtotal * (self.desc_global / 100)
    
    def calcular_totais(self):
        self.total_mercadorias = self.subtotal
        self.total_iva = sum(item.valor_iva for item in self.items)
        self.total_desconto = self.desc_valor + self.valor_desc_global
        self.valor_total = self.total_mercadorias + self.total_iva - self.total_desconto

class BudgetItem(db.Model):
    __tablename__ = 'budget_items'
    
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    service_item_id = db.Column(db.Integer, db.ForeignKey('service_items.id'))
    
    artigo = db.Column(db.String(10))
    descricao = db.Column(db.String(200), nullable=False)
    iva = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    desconto = db.Column(db.Float, default=0.0)
    
    # Campos calculados
    total = db.Column(db.Float)
    valor_iva = db.Column(db.Float)
    
    # Relacionamento
    service_item = db.relationship('ServiceItem')
    
    def __repr__(self):
        return f'<BudgetItem {self.descricao}>'
    
    def calcular_valores(self):
        self.total = self.quantidade * self.preco_unitario * (1 - self.desconto/100)
        self.valor_iva = self.total * (self.iva/100)

# Pré-cadastrar alguns serviços comuns
def criar_servicos_padrao():
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
    
    try:
        db.session.commit()
    except:
        db.session.rollback()

class Intervention(db.Model):
    """Modelo para registrar intervenções/manutenções realizadas"""
    __tablename__ = 'interventions'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('Customers.id'), nullable=False)
    data_intervencao = db.Column(db.DateTime, nullable=False)
    
    # Morada da obra
    morada_obra = db.Column(db.String(300), nullable=False)
    cidade_obra = db.Column(db.String(100))
    codigo_postal_obra = db.Column(db.String(20))
    
    # Serviço executado
    servico_executado = db.Column(db.Text, nullable=False)
    tipo_servico = db.Column(db.String(100))  # Manutenção, Instalação, Reparação, etc.
    
    # Observações
    observacoes = db.Column(db.Text)
    
    # Próxima manutenção
    proxima_manutencao = db.Column(db.Date)  # Data sugerida para próxima manutenção
    intervalo_manutencao = db.Column(db.Integer)  # Intervalo em meses
    
    # Técnico responsável
    tecnico_responsavel = db.Column(db.String(100))
    
    # Status
    status = db.Column(db.String(20), default='concluida')  # concluida, pendente, cancelada
    
    # Dados de criação
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    criado_por = db.Column(db.Integer, db.ForeignKey('Users.id'))
    
    # Relacionamentos
    cliente = db.relationship('Customer', backref='interventions')
    fotos = db.relationship('InterventionPhoto', backref='intervention', cascade='all, delete-orphan')
    criador = db.relationship('Users')
    
    def __repr__(self):
        return f'<Intervention {self.id} - {self.cliente.nome_razao_social}>'

class InterventionPhoto(db.Model):
    """Modelo para fotos das intervenções"""
    __tablename__ = 'intervention_photos'
    
    id = db.Column(db.Integer, primary_key=True)
    intervention_id = db.Column(db.Integer, db.ForeignKey('interventions.id'), nullable=False)
    
    # Arquivo da foto
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    
    # Metadados
    descricao = db.Column(db.String(200))
    tipo_foto = db.Column(db.String(50))  # antes, durante, depois, problema, solucao
    
    # Data
    data_upload = db.Column(db.DateTime, default=db.func.current_timestamp())
    uploaded_by = db.Column(db.Integer, db.ForeignKey('Users.id'))
    
    # Relacionamento
    uploader = db.relationship('Users')
    
    def __repr__(self):
        return f'<InterventionPhoto {self.filename}>'

class MaintenanceAlert(db.Model):
    """Modelo para avisos de próxima manutenção"""
    __tablename__ = 'maintenance_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('Customers.id'), nullable=False)
    intervention_id = db.Column(db.Integer, db.ForeignKey('interventions.id'))  # Opcional - pode ser baseado em intervenção
    
    # Dados do aviso
    data_prevista = db.Column(db.Date, nullable=False)
    tipo_manutencao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    prioridade = db.Column(db.String(20), default='normal')  # baixa, normal, alta, urgente
    
    # Notificações
    notificar_email = db.Column(db.Boolean, default=True)
    notificar_sms = db.Column(db.Boolean, default=False)
    notificar_whatsapp = db.Column(db.Boolean, default=False)
    
    # Status e datas
    status = db.Column(db.String(20), default='ativo')  # ativo, enviado, concluido, cancelado
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    data_notificacao = db.Column(db.DateTime)  # Quando foi enviada a notificação
    data_conclusao = db.Column(db.DateTime)  # Quando foi marcada como concluída
    
    # Configurações de repetição
    repetir = db.Column(db.Boolean, default=False)
    intervalo_repeticao = db.Column(db.Integer)  # Em meses
    
    # Relacionamentos
    cliente = db.relationship('Customer', backref='maintenance_alerts')
    intervention = db.relationship('Intervention', backref='maintenance_alerts')
    
    def __repr__(self):
        return f'<MaintenanceAlert {self.cliente.nome_razao_social} - {self.data_prevista}>'
    
    @property
    def dias_restantes(self):
        """Calcula quantos dias restam para a manutenção"""
        from datetime import date
        if self.data_prevista:
            delta = self.data_prevista - date.today()
            return delta.days
        return None
    
    @property
    def is_overdue(self):
        """Verifica se a manutenção está atrasada"""
        from datetime import date
        return self.data_prevista < date.today() if self.data_prevista else False

class MaintenanceRequest(db.Model):
    """Modelo para solicitações de manutenção via API externa"""
    __tablename__ = 'maintenance_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do cliente (pode não estar cadastrado no sistema)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    nif = db.Column(db.String(20))  # Para tentar vincular com cliente existente
    
    # Dados da solicitação
    morada_servico = db.Column(db.String(300), nullable=False)
    cidade = db.Column(db.String(100))
    codigo_postal = db.Column(db.String(20))
    
    # Detalhes do serviço
    tipo_servico = db.Column(db.String(100), nullable=False)
    descricao_problema = db.Column(db.Text)
    data_preferida = db.Column(db.Date)
    periodo_preferido = db.Column(db.String(50))  # manha, tarde, noite
    
    # Status
    status = db.Column(db.String(20), default='pendente')  # pendente, agendado, concluido, cancelado
    prioridade = db.Column(db.String(20), default='normal')
    
    # Dados de controle
    data_solicitacao = db.Column(db.DateTime, default=db.func.current_timestamp())
    ip_origem = db.Column(db.String(45))  # Para controle e segurança
    user_agent = db.Column(db.String(500))
    
    # Vinculação posterior com cliente cadastrado
    cliente_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    intervention_id = db.Column(db.Integer, db.ForeignKey('interventions.id'))  # Quando é convertida em intervenção
    
    # Relacionamentos
    cliente = db.relationship('Customer', backref='maintenance_requests')
    intervention = db.relationship('Intervention', backref='maintenance_request')
    
    def __repr__(self):
        return f'<MaintenanceRequest {self.nome} - {self.tipo_servico}>'
    
    def try_link_customer(self):
        """Tenta vincular a solicitação com um cliente existente pelo NIF"""
        if self.nif and not self.cliente_id:
            customer = Customer.query.filter_by(nif=self.nif).first()
            if customer:
                self.cliente_id = customer.id
                return True
        return False
