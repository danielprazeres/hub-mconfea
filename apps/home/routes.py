# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required
from jinja2 import TemplateNotFound
from datetime import datetime
from flask import make_response
from weasyprint import HTML, CSS
from sqlalchemy import or_
from apps.authentication.models import Customer, ServiceItem, Budget, BudgetItem
from apps import db


@blueprint.route('/index')
@login_required
def index():

    return render_template('home/index.html', segment='index')


@blueprint.route('/<template>')
@login_required
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None


@blueprint.route('/budgets')
@login_required
def budgets():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filtros
    numero = request.args.get('numero', '')
    status = request.args.get('status', '')
    nome_cliente = request.args.get('nome_cliente', '')
    nif_cliente = request.args.get('nif_cliente', '')
    
    # Query base
    query = Budget.query
    
    # Aplicar filtros
    if numero:
        query = query.filter(Budget.numero.ilike(f'%{numero}%'))
    if status:
        query = query.filter(Budget.status == status)
    if nome_cliente or nif_cliente:
        query = query.join(Budget.cliente)
        if nome_cliente:
            query = query.filter(Customer.nome_razao_social.ilike(f'%{nome_cliente}%'))
        if nif_cliente:
            query = query.filter(Customer.nif.ilike(f'%{nif_cliente}%'))
    
    # Ordenação
    query = query.order_by(Budget.data_criacao.desc())
    
    # Paginação
    budgets = query.paginate(page=page, per_page=per_page)
    
    return render_template('home/budgets.html', 
                         budgets=budgets,
                         numero=numero,
                         status=status,
                         nome_cliente=nome_cliente,
                         nif_cliente=nif_cliente,
                         segment='budgets')

@blueprint.route('/budget/new', methods=['GET', 'POST'])
@login_required
def new_budget():
    if request.method == 'POST':
        data = request.get_json()
        
        budget = Budget(
            data_doc=datetime.strptime(data['data_doc'], '%Y-%m-%d').date(),
            data_venc=datetime.strptime(data['data_venc'], '%Y-%m-%d').date() if data.get('data_venc') else None,
            moeda=data.get('moeda', 'EUR'),
            cambio=float(data.get('cambio', 1.0)),
            cod_entidade=data.get('cod_entidade'),
            cliente_id=data['cliente_id'],
            desc_global=float(data.get('desc_global', 0)),
            desc_valor=float(data.get('desc_valor', 0)),
            v_num=data.get('v_num'),
            prazo_pag=data.get('prazo_pag'),
            local_carga=data.get('local_carga'),
            local_descarga=data.get('local_descarga')
        )
        
        # Gerar número sequencial
        ultimo_budget = Budget.query.order_by(Budget.id.desc()).first()
        if ultimo_budget:
            ultimo_num = int(ultimo_budget.numero.split('/')[-1])
            novo_num = ultimo_num + 1
        else:
            novo_num = 1
        
        budget.numero = f'FT SERIE1/{novo_num}'
        
        # Adicionar itens
        for item_data in data['items']:
            item = BudgetItem(
                artigo=item_data.get('artigo'),
                descricao=item_data['descricao'],
                iva=float(item_data['iva']),
                quantidade=float(item_data['quantidade']),
                preco_unitario=float(item_data['preco_unitario']),
                desconto=float(item_data.get('desconto', 0))
            )
            
            if item_data.get('service_item_id'):
                item.service_item_id = item_data['service_item_id']
                service_item = ServiceItem.query.get(item_data['service_item_id'])
                if service_item:
                    item.artigo = service_item.codigo
            
            item.calcular_valores()
            budget.items.append(item)
        
        budget.calcular_totais()
        
        try:
            db.session.add(budget)
            db.session.commit()
            return jsonify({'success': True, 'id': budget.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    customers = Customer.query.all()
    service_items = ServiceItem.query.all()
    return render_template('home/budget-form.html',
                         customers=customers,
                         service_items=service_items,
                         segment='budgets')

@blueprint.route('/budget/<int:id>')
@login_required
def view_budget(id):
    budget = Budget.query.get_or_404(id)
    return render_template('home/budget-view.html',
                         budget=budget,
                         segment='budgets')

@blueprint.route('/budget/<int:id>/pdf')
@login_required
def budget_pdf(id):
    budget = Budget.query.get_or_404(id)
    
    empresa = {
        "nome": "GCI - Global Construções e Instalações, LDA",
        "endereco": "Rua Dom Afonso Henriques, Nº 515",
        "codigo_postal": "3700-112",
        "localidade": "Arrifana",
        "telefone": "+351 256 101 722",
        "email": "geral@gcinstalacoes.pt",
        "nif": "513461491",
        "iban": "PT50 0033 0000 00066120623 05"
    }
    
    html = render_template('home/budget-pdf.html', budget=budget, empresa=empresa)
    
    # Criar o PDF usando WeasyPrint
    pdf = HTML(string=html).write_pdf(
        stylesheets=[CSS(string='@page { size: A4; margin: 1cm }')]
    )
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=orcamento_{budget.numero}.pdf'
    return response

@blueprint.route('/api/services/search')
@login_required
def search_services():
    term = request.args.get('term', '')
    services = ServiceItem.query.filter(
        or_(
            ServiceItem.descricao.ilike(f'%{term}%'),
            ServiceItem.codigo.ilike(f'%{term}%')
        )
    ).all()
    
    return jsonify([{
        'id': s.id,
        'codigo': s.codigo,
        'descricao': s.descricao,
        'tipo': s.tipo,
        'preco_padrao': s.preco_padrao,
        'iva_padrao': s.iva_padrao
    } for s in services])

@blueprint.route('/api/services', methods=['POST'])
@login_required
def create_service():
    data = request.get_json()
    
    service = ServiceItem(
        codigo=data.get('codigo'),
        descricao=data['descricao'],
        tipo=data.get('tipo'),
        preco_padrao=float(data.get('preco_padrao', 0)),
        iva_padrao=float(data.get('iva_padrao', 23))
    )
    
    try:
        db.session.add(service)
        db.session.commit()
        return jsonify({
            'success': True,
            'id': service.id,
            'codigo': service.codigo,
            'descricao': service.descricao,
            'tipo': service.tipo,
            'preco_padrao': service.preco_padrao,
            'iva_padrao': service.iva_padrao
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@blueprint.route('/api/customers/search')
@login_required
def search_customers():
    term = request.args.get('term', '')
    customers = Customer.query.filter(
        or_(
            Customer.nome_razao_social.ilike(f'%{term}%'),
            Customer.nif.ilike(f'%{term}%')
        )
    ).all()
    
    return jsonify([{
        'id': c.id,
        'nome': c.nome_razao_social,
        'nif': c.nif,
        'morada': c.rua,
        'cod_postal': c.codigo_postal,
        'localidade': c.localidade,
        'pais': c.pais
    } for c in customers])

@blueprint.route('/budget/<int:id>/status', methods=['POST'])
@login_required
def update_budget_status(id):
    budget = Budget.query.get_or_404(id)
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({'success': False, 'error': 'Status não fornecido'}), 400
        
    new_status = data['status']
    if new_status not in ['rascunho', 'aprovado', 'rejeitado', 'faturado']:
        return jsonify({'success': False, 'error': 'Status inválido'}), 400
    
    try:
        budget.status = new_status
        db.session.commit()
        return jsonify({
            'success': True,
            'status': new_status
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================
# ROTAS PARA INTERVENÇÕES
# =====================================

@blueprint.route('/interventions')
@login_required
def interventions_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filtros
    cliente_nome = request.args.get('cliente_nome', '')
    status = request.args.get('status', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    
    # Query base
    from apps.authentication.models import Intervention
    query = Intervention.query.join(Intervention.cliente)
    
    # Aplicar filtros
    if cliente_nome:
        query = query.filter(Customer.nome_razao_social.ilike(f'%{cliente_nome}%'))
    if status:
        query = query.filter(Intervention.status == status)
    if data_inicio:
        query = query.filter(Intervention.data_intervencao >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    if data_fim:
        query = query.filter(Intervention.data_intervencao <= datetime.strptime(data_fim, '%Y-%m-%d'))
    
    # Ordenação
    query = query.order_by(Intervention.data_intervencao.desc())
    
    # Paginação
    interventions = query.paginate(page=page, per_page=per_page)
    
    return render_template('home/interventions-list.html', 
                         interventions=interventions,
                         cliente_nome=cliente_nome,
                         status=status,
                         data_inicio=data_inicio,
                         data_fim=data_fim,
                         segment='interventions')

@blueprint.route('/intervention/new', methods=['GET', 'POST'])
@login_required
def new_intervention():
    from apps.authentication.models import Intervention
    from flask_login import current_user
    
    if request.method == 'POST':
        try:
            intervention = Intervention(
                cliente_id=request.form['cliente_id'],
                data_intervencao=datetime.strptime(request.form['data_intervencao'], '%Y-%m-%dT%H:%M'),
                morada_obra=request.form['morada_obra'],
                cidade_obra=request.form.get('cidade_obra'),
                codigo_postal_obra=request.form.get('codigo_postal_obra'),
                servico_executado=request.form['servico_executado'],
                tipo_servico=request.form.get('tipo_servico'),
                observacoes=request.form.get('observacoes'),
                tecnico_responsavel=request.form.get('tecnico_responsavel'),
                status=request.form.get('status', 'concluida'),
                criado_por=current_user.id
            )
            
            # Próxima manutenção se especificada
            if request.form.get('proxima_manutencao'):
                intervention.proxima_manutencao = datetime.strptime(request.form['proxima_manutencao'], '%Y-%m-%d').date()
            
            if request.form.get('intervalo_manutencao'):
                intervention.intervalo_manutencao = int(request.form['intervalo_manutencao'])
            
            db.session.add(intervention)
            db.session.commit()
            
            # Criar aviso de manutenção se especificado
            if intervention.proxima_manutencao:
                from apps.authentication.models import MaintenanceAlert
                alert = MaintenanceAlert(
                    cliente_id=intervention.cliente_id,
                    intervention_id=intervention.id,
                    data_prevista=intervention.proxima_manutencao,
                    tipo_manutencao=f"Manutenção de {intervention.tipo_servico}",
                    descricao=f"Manutenção programada baseada na intervenção de {intervention.data_intervencao.strftime('%d/%m/%Y')}",
                    repetir=True if intervention.intervalo_manutencao else False,
                    intervalo_repeticao=intervention.intervalo_manutencao
                )
                db.session.add(alert)
                db.session.commit()
            
            return redirect(url_for('home_blueprint.view_intervention', id=intervention.id))
            
        except Exception as e:
            db.session.rollback()
            return render_template('home/intervention-form.html',
                                 customers=Customer.query.all(),
                                 error=f'Erro ao criar intervenção: {str(e)}',
                                 segment='interventions')
    
    customers = Customer.query.all()
    return render_template('home/intervention-form.html',
                         customers=customers,
                         segment='interventions')

@blueprint.route('/intervention/<int:id>')
@login_required
def view_intervention(id):
    from apps.authentication.models import Intervention
    intervention = Intervention.query.get_or_404(id)
    return render_template('home/intervention-view.html',
                         intervention=intervention,
                         segment='interventions')

@blueprint.route('/intervention/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_intervention(id):
    from apps.authentication.models import Intervention
    intervention = Intervention.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            intervention.cliente_id = request.form['cliente_id']
            intervention.data_intervencao = datetime.strptime(request.form['data_intervencao'], '%Y-%m-%dT%H:%M')
            intervention.morada_obra = request.form['morada_obra']
            intervention.cidade_obra = request.form.get('cidade_obra')
            intervention.codigo_postal_obra = request.form.get('codigo_postal_obra')
            intervention.servico_executado = request.form['servico_executado']
            intervention.tipo_servico = request.form.get('tipo_servico')
            intervention.observacoes = request.form.get('observacoes')
            intervention.tecnico_responsavel = request.form.get('tecnico_responsavel')
            intervention.status = request.form.get('status', 'concluida')
            
            if request.form.get('proxima_manutencao'):
                intervention.proxima_manutencao = datetime.strptime(request.form['proxima_manutencao'], '%Y-%m-%d').date()
            
            if request.form.get('intervalo_manutencao'):
                intervention.intervalo_manutencao = int(request.form['intervalo_manutencao'])
            
            db.session.commit()
            return redirect(url_for('home_blueprint.view_intervention', id=intervention.id))
            
        except Exception as e:
            db.session.rollback()
            return render_template('home/intervention-edit.html',
                                 intervention=intervention,
                                 customers=Customer.query.all(),
                                 error=f'Erro ao atualizar intervenção: {str(e)}',
                                 segment='interventions')
    
    customers = Customer.query.all()
    return render_template('home/intervention-edit.html',
                         intervention=intervention,
                         customers=customers,
                         segment='interventions')

# =====================================
# ROTAS PARA AVISOS DE MANUTENÇÃO
# =====================================

@blueprint.route('/maintenance-alerts')
@login_required
def maintenance_alerts():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    # Filtros
    cliente_nome = request.args.get('cliente_nome', '')
    status = request.args.get('status', '')
    prioridade = request.args.get('prioridade', '')
    vencidos = request.args.get('vencidos', '')
    
    # Query base
    from apps.authentication.models import MaintenanceAlert
    query = MaintenanceAlert.query.join(MaintenanceAlert.cliente)
    
    # Aplicar filtros
    if cliente_nome:
        query = query.filter(Customer.nome_razao_social.ilike(f'%{cliente_nome}%'))
    if status:
        query = query.filter(MaintenanceAlert.status == status)
    if prioridade:
        query = query.filter(MaintenanceAlert.prioridade == prioridade)
    if vencidos == 'sim':
        from datetime import date
        query = query.filter(MaintenanceAlert.data_prevista < date.today())
    
    # Ordenação - vencidos primeiro, depois por data prevista
    from datetime import date
    from sqlalchemy import case
    query = query.order_by(
        case(
            (MaintenanceAlert.data_prevista < date.today(), 0),
            else_=1
        ),
        MaintenanceAlert.data_prevista.asc()
    )
    
    # Paginação
    alerts = query.paginate(page=page, per_page=per_page)
    
    return render_template('home/maintenance-alerts.html',
                         alerts=alerts,
                         cliente_nome=cliente_nome,
                         status=status,
                         prioridade=prioridade,
                         vencidos=vencidos,
                         segment='maintenance-alerts')

@blueprint.route('/maintenance-alert/new', methods=['GET', 'POST'])
@login_required
def new_maintenance_alert():
    from apps.authentication.models import MaintenanceAlert
    
    if request.method == 'POST':
        try:
            alert = MaintenanceAlert(
                cliente_id=request.form['cliente_id'],
                data_prevista=datetime.strptime(request.form['data_prevista'], '%Y-%m-%d').date(),
                tipo_manutencao=request.form['tipo_manutencao'],
                descricao=request.form.get('descricao'),
                prioridade=request.form.get('prioridade', 'normal'),
                notificar_email=bool(request.form.get('notificar_email')),
                notificar_sms=bool(request.form.get('notificar_sms')),
                notificar_whatsapp=bool(request.form.get('notificar_whatsapp')),
                repetir=bool(request.form.get('repetir')),
                intervalo_repeticao=int(request.form['intervalo_repeticao']) if request.form.get('intervalo_repeticao') else None
            )
            
            db.session.add(alert)
            db.session.commit()
            
            return redirect(url_for('home_blueprint.maintenance_alerts'))
            
        except Exception as e:
            db.session.rollback()
            return render_template('home/maintenance-alert-form.html',
                                 customers=Customer.query.all(),
                                 error=f'Erro ao criar aviso: {str(e)}',
                                 segment='maintenance-alerts')
    
    customers = Customer.query.all()
    return render_template('home/maintenance-alert-form.html',
                         customers=customers,
                         segment='maintenance-alerts')

# =====================================
# ROTAS PARA SOLICITAÇÕES EXTERNAS  
# =====================================

@blueprint.route('/maintenance-requests')
@login_required
def maintenance_requests():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    # Filtros
    nome = request.args.get('nome', '')
    status = request.args.get('status', '')
    tipo_servico = request.args.get('tipo_servico', '')
    
    # Query base
    from apps.authentication.models import MaintenanceRequest
    query = MaintenanceRequest.query
    
    # Aplicar filtros
    if nome:
        query = query.filter(MaintenanceRequest.nome.ilike(f'%{nome}%'))
    if status:
        query = query.filter(MaintenanceRequest.status == status)
    if tipo_servico:
        query = query.filter(MaintenanceRequest.tipo_servico.ilike(f'%{tipo_servico}%'))
    
    # Ordenação
    query = query.order_by(MaintenanceRequest.data_solicitacao.desc())
    
    # Paginação
    requests = query.paginate(page=page, per_page=per_page)
    
    return render_template('home/maintenance-requests.html',
                         requests=requests,
                         nome=nome,
                         status=status,
                         tipo_servico=tipo_servico,
                         segment='maintenance-requests')

@blueprint.route('/maintenance-request/<int:id>')
@login_required
def view_maintenance_request(id):
    from apps.authentication.models import MaintenanceRequest
    request_obj = MaintenanceRequest.query.get_or_404(id)
    return render_template('home/maintenance-request-view.html',
                         request_obj=request_obj,
                         segment='maintenance-requests')

# =====================================
# API EXTERNA PARA SOLICITAÇÕES
# =====================================

@blueprint.route('/api/maintenance-request', methods=['POST'])
def api_maintenance_request():
    """API endpoint para solicitações externas de manutenção"""
    try:
        data = request.get_json()
        
        # Validação básica
        required_fields = ['nome', 'email', 'morada_servico', 'tipo_servico']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400
        
        from apps.authentication.models import MaintenanceRequest
        
        # Criar solicitação
        maintenance_request = MaintenanceRequest(
            nome=data['nome'],
            email=data['email'],
            telefone=data.get('telefone'),
            nif=data.get('nif'),
            morada_servico=data['morada_servico'],
            cidade=data.get('cidade'),
            codigo_postal=data.get('codigo_postal'),
            tipo_servico=data['tipo_servico'],
            descricao_problema=data.get('descricao_problema'),
            data_preferida=datetime.strptime(data['data_preferida'], '%Y-%m-%d').date() if data.get('data_preferida') else None,
            periodo_preferido=data.get('periodo_preferido'),
            prioridade=data.get('prioridade', 'normal'),
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        # Tentar vincular com cliente existente
        maintenance_request.try_link_customer()
        
        db.session.add(maintenance_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'id': maintenance_request.id,
            'message': 'Solicitação recebida com sucesso. Entraremos em contato em breve.'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor'
        }), 500

@blueprint.route('/api/maintenance-request/<int:id>/status', methods=['PUT'])
@login_required
def update_maintenance_request_status(id):
    """Atualizar status de solicitação de manutenção"""
    from apps.authentication.models import MaintenanceRequest
    
    try:
        request_obj = MaintenanceRequest.query.get_or_404(id)
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({'success': False, 'error': 'Status não fornecido'}), 400
            
        new_status = data['status']
        if new_status not in ['pendente', 'agendado', 'concluido', 'cancelado']:
            return jsonify({'success': False, 'error': 'Status inválido'}), 400
        
        request_obj.status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'status': new_status
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
