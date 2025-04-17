# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, request, jsonify
from flask_login import login_required
from jinja2 import TemplateNotFound
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import make_response
from weasyprint import HTML
from sqlalchemy import or_
from apps.authentication.models import Customer, ServiceItem, Budget, BudgetItem

db = SQLAlchemy()


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
    
    budgets = Budget.query.order_by(Budget.data_criacao.desc()).paginate(page=page, per_page=per_page)
    return render_template('home/budgets.html', 
                         budgets=budgets,
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
                artigo=item_data['artigo'],
                descricao=item_data['descricao'],
                iva=float(item_data['iva']),
                quantidade=float(item_data['quantidade']),
                preco_unitario=float(item_data['preco_unitario']),
                desconto=float(item_data.get('desconto', 0))
            )
            
            if item_data.get('service_item_id'):
                item.service_item_id = item_data['service_item_id']
            
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
    
    # Gerar PDF usando WeasyPrint
    html = render_template('home/budget-pdf.html', budget=budget)
    pdf = HTML(string=html).write_pdf()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=orcamento_{budget.numero}.pdf'
    
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
