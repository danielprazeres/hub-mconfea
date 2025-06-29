# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import render_template, redirect, request, url_for
from flask_login import (
    current_user,
    login_user,
    logout_user
)
from werkzeug.utils import secure_filename
import os

from flask_dance.contrib.github import github

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm, CustomerForm
from apps.authentication.models import Users, Customer

from apps.authentication.util import verify_pass

from datetime import datetime


@blueprint.route('/')
def route_default():
    return redirect(url_for('authentication_blueprint.login'))

# Login & Registration

@blueprint.route("/github")
def login_github():
    """ Github login """
    if not github.authorized:
        return redirect(url_for("github.login"))

    res = github.get("/user")
    return redirect(url_for('home_blueprint.index'))
    
@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        # read form data
        username = request.form['username']
        password = request.form['password']

        # Locate user
        user = Users.query.filter_by(username=username).first()

        # Check the password
        if user and verify_pass(password, user.password):

            login_user(user)
            return redirect(url_for('authentication_blueprint.route_default'))

        # Something (user or pass) is not ok
        return render_template('accounts/login.html',
                               msg='Wrong user or password',
                               form=login_form)

    if not current_user.is_authenticated:
        return render_template('accounts/login.html',
                               form=login_form)
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']

        # Check usename exists
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Username already registered',
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Email already registered',
                                   success=False,
                                   form=create_account_form)

        # else we can create the user
        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()

        # Delete user from session
        logout_user()
        
        return render_template('accounts/register.html',
                               msg='Account created successfully.',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('accounts/register.html', form=create_account_form)


@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('authentication_blueprint.login'))


@blueprint.route('/profile')
def profile():
    if not current_user.is_authenticated:
        return redirect(url_for('authentication_blueprint.login'))
    return render_template('home/profile.html',
                       current_user=current_user,
                       current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))


@blueprint.route('/upload-photo', methods=['POST'])
def upload_photo():
    if not current_user.is_authenticated:
        return redirect(url_for('authentication_blueprint.login'))
    
    if 'photo' not in request.files:
        return render_template('home/profile.html',
                           current_user=current_user,
                           current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                           photo_msg='Nenhum arquivo selecionado',
                           photo_success=False)
    
    photo = request.files['photo']
    
    if photo.filename == '':
        return render_template('home/profile.html',
                           current_user=current_user,
                           current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                           photo_msg='Nenhum arquivo selecionado',
                           photo_success=False)
    
    if photo:
        try:
            # Garante que o nome do arquivo é seguro
            filename = secure_filename(photo.filename)
            # Gera um nome único para o arquivo
            unique_filename = f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            # Define o caminho para salvar a foto
            upload_folder = os.path.join('apps', 'static', 'assets', 'img', 'profile_photos')
            # Cria o diretório se não existir
            os.makedirs(upload_folder, exist_ok=True)
            # Caminho completo do arquivo
            filepath = os.path.join(upload_folder, unique_filename)
            # Salva o arquivo
            photo.save(filepath)
            # Atualiza o caminho no banco de dados
            current_user.profile_photo = f'img/profile_photos/{unique_filename}'
            db.session.commit()
            
            return render_template('home/profile.html',
                               current_user=current_user,
                               current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                               photo_msg='Foto atualizada com sucesso',
                               photo_success=True)
        except Exception as e:
            db.session.rollback()
            return render_template('home/profile.html',
                               current_user=current_user,
                               current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                               photo_msg=f'Erro ao atualizar foto: {str(e)}',
                               photo_success=False)


@blueprint.route('/change-password', methods=['POST'])
def change_password():
    if not current_user.is_authenticated:
        return redirect(url_for('authentication_blueprint.login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not verify_pass(current_password, current_user.password):
        return render_template('home/profile.html',
                           current_user=current_user,
                           current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                           password_msg='Senha atual incorreta',
                           password_success=False)
    
    if new_password != confirm_password:
        return render_template('home/profile.html',
                           current_user=current_user,
                           current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                           password_msg='As senhas não coincidem',
                           password_success=False)
    
    try:
        from apps.authentication.util import hash_pass
        current_user.password = hash_pass(new_password)
        db.session.commit()
        
        return render_template('home/profile.html',
                           current_user=current_user,
                           current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                           password_msg='Senha alterada com sucesso',
                           password_success=True)
    except Exception as e:
        db.session.rollback()
        return render_template('home/profile.html',
                           current_user=current_user,
                           current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                           password_msg='Erro ao alterar senha. Por favor, tente novamente.',
                           password_success=False)


# Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500


@blueprint.route('/customers', methods=['GET', 'POST'])
def customers():
    form = CustomerForm(request.form)
    
    if request.method == 'POST':
        try:
            customer = Customer(
                nome_razao_social=request.form.get('nome_razao_social'),
                nif=request.form.get('nif'),
                tipo_cliente=request.form.get('tipo_cliente'),
                morada=request.form.get('morada'),
                rua=request.form.get('rua'),
                numero=request.form.get('numero'),
                lote=request.form.get('lote'),
                complemento=request.form.get('complemento'),
                codigo_postal=request.form.get('codigo_postal'),
                cidade=request.form.get('cidade'),
                localidade=request.form.get('localidade'),
                concelho=request.form.get('concelho'),
                distrito=request.form.get('distrito'),
                pais=request.form.get('pais'),
                telefone=request.form.get('telefone'),
                email=request.form.get('email'),
                pessoa_contato=request.form.get('pessoa_contato'),
                razao_social=request.form.get('razao_social'),
                cae=request.form.get('cae'),
                nipc=request.form.get('nipc'),
                iban=request.form.get('iban'),
                metodo_pagamento=request.form.get('metodo_pagamento'),
                condicoes_pagamento=request.form.get('condicoes_pagamento'),
                observacoes=request.form.get('observacoes')
            )
            
            db.session.add(customer)
            db.session.commit()
            
            return render_template('home/customers.html',
                               msg='Cliente cadastrado com sucesso!',
                               form=form,
                               current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
                               
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao cadastrar cliente: {str(e)}")  # Log do erro
            return render_template('home/customers.html',
                               msg=f'Erro ao cadastrar cliente: {str(e)}',
                               form=form,
                               current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    
    return render_template('home/customers.html',
                       form=form,
                       current_time=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))

@blueprint.route('/customers-list')
def customers_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # número de itens por página
    
    # Filtros
    nome = request.args.get('nome', '')
    nif = request.args.get('nif', '')
    tipo_cliente = request.args.get('tipo_cliente', '')
    cidade = request.args.get('cidade', '')
    
    # Query base
    query = Customer.query
    
    # Aplicar filtros se fornecidos
    if nome:
        query = query.filter(Customer.nome_razao_social.ilike(f'%{nome}%'))
    if nif:
        query = query.filter(Customer.nif.ilike(f'%{nif}%'))
    if tipo_cliente:
        query = query.filter(Customer.tipo_cliente == tipo_cliente)
    if cidade:
        query = query.filter(Customer.cidade.ilike(f'%{cidade}%'))
    
    # Ordenar por nome
    query = query.order_by(Customer.nome_razao_social)
    
    # Paginar resultados
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    customers = pagination.items
    
    return render_template('home/customers-list.html',
                       customers=customers,
                       pagination=pagination)

@blueprint.route('/customer-details/<int:id>')
def customer_details(id):
    customer = Customer.query.get_or_404(id)
    return render_template('home/customer-details.html', customer=customer)

@blueprint.route('/customer-edit/<int:id>', methods=['GET', 'POST'])
def customer_edit(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Atualizar dados do cliente
            customer.nome_razao_social = request.form['nome_razao_social']
            customer.nif = request.form['nif']
            customer.tipo_cliente = request.form['tipo_cliente']
            customer.morada = request.form.get('morada')
            customer.rua = request.form['rua']
            customer.numero = request.form['numero']
            customer.lote = request.form.get('lote')
            customer.complemento = request.form['complemento']
            customer.codigo_postal = request.form['codigo_postal']
            customer.cidade = request.form.get('cidade')
            customer.localidade = request.form['localidade']
            customer.concelho = request.form['concelho']
            customer.distrito = request.form['distrito']
            customer.telefone = request.form['telefone']
            customer.email = request.form['email']
            customer.pessoa_contato = request.form['pessoa_contato']
            
            if customer.tipo_cliente == 'coletiva':
                customer.razao_social = request.form['razao_social']
                customer.cae = request.form['cae']
                customer.nipc = request.form['nipc']
            
            customer.iban = request.form['iban']
            customer.metodo_pagamento = request.form['metodo_pagamento']
            customer.condicoes_pagamento = request.form['condicoes_pagamento']
            customer.observacoes = request.form['observacoes']
            
            db.session.commit()
            return redirect(url_for('authentication_blueprint.customer_details', id=customer.id))
            
        except Exception as e:
            db.session.rollback()
            return render_template('home/customer-edit.html',
                               customer=customer,
                               error='Erro ao atualizar cliente. Por favor, tente novamente.')
    
    return render_template('home/customer-edit.html', customer=customer)
