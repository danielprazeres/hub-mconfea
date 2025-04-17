# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import Email, DataRequired

# login and registration


class LoginForm(FlaskForm):
    username = StringField('Username',
                         id='username_login',
                         validators=[DataRequired()])
    password = PasswordField('Password',
                             id='pwd_login',
                             validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField('Username',
                         id='username_create',
                         validators=[DataRequired()])
    email = StringField('Email',
                      id='email_create',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             id='pwd_create',
                             validators=[DataRequired()])


class CustomerForm(FlaskForm):
    # Identificação Fiscal
    nome_razao_social = StringField('Nome/Razão Social', validators=[DataRequired()])
    nif = StringField('NIF', validators=[DataRequired()])
    tipo_cliente = StringField('Tipo de Cliente', validators=[DataRequired()])
    
    # Endereço Fiscal
    endereco_completo = StringField('Endereço Completo')
    rua_avenida = StringField('Rua/Avenida')
    numero_andar_porta = StringField('Número/Andar/Porta')
    codigo_postal = StringField('Código Postal')
    localidade = StringField('Localidade')
    distrito = StringField('Distrito')
    pais = StringField('País')
    
    # Contato
    telefone = StringField('Telefone')
    email = StringField('Email', validators=[Email()])
    pessoa_contato = StringField('Pessoa de Contato')
    
    # Dados Empresariais
    nome_empresa = StringField('Nome da Empresa')
    cae = StringField('CAE')
    nipc = StringField('NIPC')
    
    # Faturamento/Pagamento
    iban = StringField('IBAN')
    metodo_pagamento = StringField('Método de Pagamento')
    condicoes_pagamento = StringField('Condições de Pagamento')
    
    # Outros
    observacoes = TextAreaField('Observações')
