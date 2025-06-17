from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.tournament import Atleta, Torneio, Categoria, Inscricao, Jogo, Resultado, Chaveamento
from datetime import datetime
import json

tournament_bp = Blueprint('tournament', __name__)

# ===== ROTAS DE ATLETAS =====

@tournament_bp.route('/atletas', methods=['GET'])
def get_atletas():
    """Listar todos os atletas com filtros opcionais"""
    try:
        categoria = request.args.get('categoria')
        pais = request.args.get('pais')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = Atleta.query.filter_by(ativo=True)
        
        if categoria:
            query = query.filter_by(categoria=categoria)
        if pais:
            query = query.filter_by(pais=pais)
            
        # Ordenar por ranking
        query = query.order_by(Atleta.ranking_posicao.asc().nullslast())
        
        atletas = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'atletas': [atleta.to_dict() for atleta in atletas.items],
            'total': atletas.total,
            'pages': atletas.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/atletas/<int:atleta_id>', methods=['GET'])
def get_atleta(atleta_id):
    """Obter detalhes de um atleta específico"""
    try:
        atleta = Atleta.query.get_or_404(atleta_id)
        
        # Buscar histórico de resultados
        resultados = Resultado.query.filter_by(atleta_id=atleta_id).order_by(Resultado.data_resultado.desc()).limit(10).all()
        
        # Buscar próximos jogos
        proximos_jogos = db.session.query(Jogo).join(Inscricao, 
            (Jogo.equipe1_id == Inscricao.id) | (Jogo.equipe2_id == Inscricao.id)
        ).filter(
            Inscricao.atleta_id == atleta_id,
            Jogo.status.in_(['agendado', 'em_andamento'])
        ).order_by(Jogo.data_hora.asc()).limit(5).all()
        
        return jsonify({
            'atleta': atleta.to_dict(),
            'resultados_recentes': [resultado.to_dict() for resultado in resultados],
            'proximos_jogos': [jogo.to_dict() for jogo in proximos_jogos]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/atletas', methods=['POST'])
def create_atleta():
    """Criar novo atleta"""
    try:
        data = request.get_json()
        
        # Verificar se email já existe
        if Atleta.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email já cadastrado'}), 400
        
        atleta = Atleta(
            nome=data['nome'],
            email=data['email'],
            data_nascimento=datetime.strptime(data.get('data_nascimento'), '%Y-%m-%d').date() if data.get('data_nascimento') else None,
            altura=data.get('altura'),
            peso=data.get('peso'),
            pais=data.get('pais'),
            foto_url=data.get('foto_url'),
            categoria=data.get('categoria')
        )
        
        db.session.add(atleta)
        db.session.commit()
        
        return jsonify(atleta.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/ranking', methods=['GET'])
def get_ranking():
    """Obter ranking geral ou por categoria"""
    try:
        categoria = request.args.get('categoria')
        limit = int(request.args.get('limit', 50))
        
        query = Atleta.query.filter_by(ativo=True)
        
        if categoria:
            query = query.filter_by(categoria=categoria)
            
        atletas = query.order_by(Atleta.ranking_posicao.asc().nullslast()).limit(limit).all()
        
        return jsonify({
            'ranking': [atleta.to_dict() for atleta in atletas],
            'categoria': categoria or 'Geral'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ROTAS DE TORNEIOS =====

@tournament_bp.route('/torneios', methods=['GET'])
def get_torneios():
    """Listar torneios com filtros"""
    try:
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        query = Torneio.query
        
        if status:
            query = query.filter_by(status=status)
            
        torneios = query.order_by(Torneio.data_inicio.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'torneios': [torneio.to_dict() for torneio in torneios.items],
            'total': torneios.total,
            'pages': torneios.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/torneios/<int:torneio_id>', methods=['GET'])
def get_torneio(torneio_id):
    """Obter detalhes de um torneio"""
    try:
        torneio = Torneio.query.get_or_404(torneio_id)
        categorias = Categoria.query.filter_by(torneio_id=torneio_id).all()
        
        # Contar inscrições por categoria
        for categoria in categorias:
            categoria.total_inscricoes = Inscricao.query.filter_by(categoria_id=categoria.id, status='confirmada').count()
        
        return jsonify({
            'torneio': torneio.to_dict(),
            'categorias': [categoria.to_dict() for categoria in categorias]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/torneios', methods=['POST'])
def create_torneio():
    """Criar novo torneio"""
    try:
        data = request.get_json()
        
        torneio = Torneio(
            nome=data['nome'],
            descricao=data.get('descricao'),
            local=data.get('local'),
            data_inicio=datetime.strptime(data['data_inicio'], '%Y-%m-%d').date(),
            data_fim=datetime.strptime(data['data_fim'], '%Y-%m-%d').date(),
            tipo_chaveamento=data.get('tipo_chaveamento', 'eliminacao_simples'),
            max_participantes=data.get('max_participantes'),
            premio_total=data.get('premio_total'),
            organizador_id=data.get('organizador_id')
        )
        
        db.session.add(torneio)
        db.session.commit()
        
        return jsonify(torneio.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== ROTAS DE CHAVEAMENTO =====

@tournament_bp.route('/torneios/<int:torneio_id>/chaveamento/<int:categoria_id>', methods=['GET'])
def get_chaveamento(torneio_id, categoria_id):
    """Obter chaveamento de uma categoria"""
    try:
        chaveamento = Chaveamento.query.filter_by(torneio_id=torneio_id, categoria_id=categoria_id).first()
        
        if not chaveamento:
            return jsonify({'error': 'Chaveamento não encontrado'}), 404
            
        # Buscar jogos da categoria
        jogos = Jogo.query.filter_by(torneio_id=torneio_id, categoria_id=categoria_id).all()
        
        return jsonify({
            'chaveamento': chaveamento.to_dict(),
            'jogos': [jogo.to_dict() for jogo in jogos]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/torneios/<int:torneio_id>/chaveamento/<int:categoria_id>/gerar', methods=['POST'])
def gerar_chaveamento(torneio_id, categoria_id):
    """Gerar chaveamento para uma categoria"""
    try:
        # Buscar inscrições confirmadas
        inscricoes = Inscricao.query.filter_by(
            torneio_id=torneio_id, 
            categoria_id=categoria_id, 
            status='confirmada'
        ).all()
        
        if len(inscricoes) < 2:
            return jsonify({'error': 'Número insuficiente de participantes'}), 400
        
        # Gerar estrutura básica do chaveamento
        import random
        random.shuffle(inscricoes)
        
        estrutura = {
            'participantes': [inscricao.to_dict() for inscricao in inscricoes],
            'fases': [],
            'tipo': 'eliminacao_simples'
        }
        
        # Criar ou atualizar chaveamento
        chaveamento = Chaveamento.query.filter_by(torneio_id=torneio_id, categoria_id=categoria_id).first()
        
        if chaveamento:
            chaveamento.estrutura_json = json.dumps(estrutura)
            chaveamento.data_atualizacao = datetime.utcnow()
        else:
            chaveamento = Chaveamento(
                torneio_id=torneio_id,
                categoria_id=categoria_id,
                estrutura_json=json.dumps(estrutura)
            )
            db.session.add(chaveamento)
        
        # Gerar jogos da primeira fase
        for i in range(0, len(inscricoes), 2):
            if i + 1 < len(inscricoes):
                jogo = Jogo(
                    torneio_id=torneio_id,
                    categoria_id=categoria_id,
                    fase='primeira_fase',
                    rodada=1,
                    equipe1_id=inscricoes[i].id,
                    equipe2_id=inscricoes[i + 1].id
                )
                db.session.add(jogo)
        
        db.session.commit()
        
        return jsonify(chaveamento.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== ROTAS DE JOGOS =====

@tournament_bp.route('/jogos/<int:jogo_id>/resultado', methods=['POST'])
def inserir_resultado(jogo_id):
    """Inserir resultado de um jogo"""
    try:
        data = request.get_json()
        jogo = Jogo.query.get_or_404(jogo_id)
        
        jogo.placar_equipe1 = data['placar_equipe1']
        jogo.placar_equipe2 = data['placar_equipe2']
        jogo.status = 'finalizado'
        jogo.observacoes = data.get('observacoes')
        
        db.session.commit()
        
        # Atualizar ranking dos atletas (implementar lógica de pontuação)
        # TODO: Implementar sistema de pontuação
        
        return jsonify(jogo.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/torneios/<int:torneio_id>/jogos', methods=['GET'])
def get_jogos_torneio(torneio_id):
    """Obter jogos de um torneio"""
    try:
        categoria_id = request.args.get('categoria_id')
        status = request.args.get('status')
        
        query = Jogo.query.filter_by(torneio_id=torneio_id)
        
        if categoria_id:
            query = query.filter_by(categoria_id=categoria_id)
        if status:
            query = query.filter_by(status=status)
            
        jogos = query.order_by(Jogo.data_hora.asc()).all()
        
        return jsonify({
            'jogos': [jogo.to_dict() for jogo in jogos]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ROTAS DE INSCRIÇÕES =====

@tournament_bp.route('/inscricoes', methods=['POST'])
def criar_inscricao():
    """Criar nova inscrição"""
    try:
        data = request.get_json()
        
        # Verificar se atleta já está inscrito na categoria
        inscricao_existente = Inscricao.query.filter_by(
            torneio_id=data['torneio_id'],
            categoria_id=data['categoria_id'],
            atleta_id=data['atleta_id']
        ).first()
        
        if inscricao_existente:
            return jsonify({'error': 'Atleta já inscrito nesta categoria'}), 400
        
        inscricao = Inscricao(
            torneio_id=data['torneio_id'],
            categoria_id=data['categoria_id'],
            atleta_id=data['atleta_id'],
            parceiro_id=data.get('parceiro_id'),
            nome_equipe=data.get('nome_equipe')
        )
        
        db.session.add(inscricao)
        db.session.commit()
        
        return jsonify(inscricao.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tournament_bp.route('/torneios/<int:torneio_id>/inscricoes', methods=['GET'])
def get_inscricoes_torneio(torneio_id):
    """Obter inscrições de um torneio"""
    try:
        categoria_id = request.args.get('categoria_id')
        
        query = Inscricao.query.filter_by(torneio_id=torneio_id)
        
        if categoria_id:
            query = query.filter_by(categoria_id=categoria_id)
            
        inscricoes = query.all()
        
        return jsonify({
            'inscricoes': [inscricao.to_dict() for inscricao in inscricoes]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

