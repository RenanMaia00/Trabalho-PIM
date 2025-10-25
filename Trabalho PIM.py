from datetime import datetime
import json
import os # Importa o módulo os para verificar a existência do arquivo

# --- Configurações Globais 
MEDIA_APROVACAO = 7.0
PERCENTUAL_FREQUENCIA_MINIMA = 75.0
ARQUIVO_DADOS = 'sistema_academico_dados.json' # Nome do arquivo para armazenamento

# --- Funções Auxiliares de Conversão

def to_dict(obj):
    #Converte um objeto de classe em um dicionário para JSON
    if isinstance(obj, (Usuario, Professor, Aluno, Disciplina)):
        # Obtém o dicionário interno
        data = obj.__dict__.copy()
        data['__class__'] = obj.__class__.__name__
       
        if 'senha' in data:
             data.pop('senha') 
             
        # Lógica especial para classes filhas
        if isinstance(obj, Professor):
            data['disciplinas_ministradas'] = obj.disciplinas_ministradas
        
        return data
    raise TypeError(f"Objeto do tipo {type(obj)} não é serializável em JSON.")

def from_dict(data):
    #Converte um dicionário de volta para um objeto de classe
    if '__class__' in data:
        class_name = data.pop('__class__')
     
        # Reconstrução dos objetos
        if class_name == 'Usuario':
            # Usuários genéricos (admin/secretaria)
            return Usuario(data['login'], '123', data['nome'], data['perfil'])
        
        elif class_name == 'Professor':
            # Professor
            professor = Professor(data['login'], '123', data['nome'])
            professor.disciplinas_ministradas = data.get('disciplinas_ministradas', [])
            return professor
        
        elif class_name == 'Aluno':
            # Aluno
            aluno = Aluno(data['login'], '123', data['nome'], data['ra'])
            aluno.cursos = data.get('cursos', {})
            aluno.frequencias = data.get('frequencias', {})
            aluno.notas = data.get('notas', {})
            aluno.dados_pessoais = data.get('dados_pessoais', {})
            return aluno
            
        elif class_name == 'Disciplina':
            # Disciplina
            disc = Disciplina(data['id'], data['nome'], data.get('professor_login'))
            disc.alunos_ra = data.get('alunos_ra', [])
            return disc
            
    return data # Retorna o dicionário se não for um objeto de classe conhecido

# --- JSON Encoder Customizado para lidar com classes
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            # Tenta usar a função de conversão customizada
            return to_dict(obj)
        except TypeError:
            # Fallback para o comportamento padrão do JSONEncoder
            return json.JSONEncoder.default(self, obj)

# --- Classes de Entidades

class Usuario:
    def __init__(self, login, senha, nome, perfil):
        self.login = login
        self.senha = senha
        self.nome = nome
        self.perfil = perfil

class Disciplina:
    def __init__(self, id_disciplina, nome, professor_login=None):
        self.id = id_disciplina
        self.nome = nome
        self.professor_login = professor_login
        self.alunos_ra = []

class Professor(Usuario):
    # Chama o construtor da classe base (Usuario) passando o perfil 'professor'.
    def __init__(self, login, senha, nome):
        super().__init__(login, senha, nome, 'professor')
        self.disciplinas_ministradas = []

class Aluno(Usuario):
    #Chama o construtor da classe base (Usuario) passando o perfil 'aluno'.
    def __init__(self, login, senha, nome, ra):
        super().__init__(login, senha, nome, 'aluno') 
        self.ra = ra
        self.cursos = {} 
        self.frequencias = {} 
        self.notas = {} 
        self.dados_pessoais = {} 

    def calcular_media(self, id_disciplina):
        notas_disciplina = self.notas.get(id_disciplina, [])
        if notas_disciplina:
            return sum(notas_disciplina) / len(notas_disciplina)
        return 0.0

    def verificar_aprovacao(self, id_disciplina):
        media = self.calcular_media(id_disciplina)
        aprovado_nota = media >= MEDIA_APROVACAO
        frequencias = self.frequencias.get(id_disciplina, [])
        total_aulas = len(frequencias)
        total_presencas = sum(1 for f in frequencias if f['tipo'] == 'P')
        freq_percentual = (total_presencas / total_aulas * 100) if total_aulas > 0 else 100.0
        aprovado_frequencia = freq_percentual >= PERCENTUAL_FREQUENCIA_MINIMA

        if not aprovado_frequencia:
            return "REPROVADO POR FALTA", freq_percentual, media
        if not aprovado_nota:
            return "REPROVADO POR NOTA", freq_percentual, media
        
        return "APROVADO", freq_percentual, media

# --- Gerenciamento de Dados (Simulação de DAO/Banco)
class SistemaAcademico:
    def __init__(self):
        self.usuarios = {}  
        self.alunos = {}  
        self.professores = {} 
        self.disciplinas = {} 
        self.carregar_dados()
        # Salva o estado inicial, garantindo que o arquivo seja criado com admin/secretaria se não existir
        self.salvar_dados() 

    def carregar_dados_iniciais(self):
        # Usuários e Perfis Iniciais
        admin = Usuario('admin', '123', 'Admin Master', 'administrador')
        sec = Usuario('secretaria1', '123', 'Ana Secretária', 'secretaria')

        self.usuarios = {u.login: u for u in [admin, sec]}
        self.professores = {}
        self.alunos = {}
        self.disciplinas = {} 

    def salvar_dados(self):
        #Salva o estado atual do sistema em um arquivo JSON
        
        usuarios_base = {k: v for k, v in self.usuarios.items() if v.perfil in ['administrador', 'secretaria']}
        
        for login in list(usuarios_base.keys()):
            if login in self.professores or login in {a.login for a in self.alunos.values()}:
                usuarios_base.pop(login)
                
        data = {
            'usuarios': usuarios_base,
            'professores': self.professores,
            'alunos': {k: v for k, v in self.alunos.items()},
            'disciplinas': self.disciplinas
        }
        
        try:
            with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, cls=CustomEncoder, ensure_ascii=False)
            # print(f"\n[INFO] Dados salvos em {ARQUIVO_DADOS}.")
        except Exception as e:
            print(f"[ERRO] Falha ao salvar dados: {e}")

    def carregar_dados(self):
        #Carrega o estado do sistema a partir de um arquivo JSON
        if not os.path.exists(ARQUIVO_DADOS):
             print(f"[AVISO] Arquivo {ARQUIVO_DADOS} não encontrado. Iniciando com dados padrão.")
             self.carregar_dados_iniciais()
             return

        try:
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                data = json.load(f, object_hook=from_dict)
                
                # Reseta e popula as estruturas de dados
                self.usuarios = {}
                self.professores = data.get('professores', {})
                self.alunos = data.get('alunos', {})
                self.disciplinas = data.get('disciplinas', {})
                
                # 1. Popula o dicionário de usuários com Alunos e Professores
                self.usuarios.update(self.professores) 
                self.usuarios.update({a.login: a for a in self.alunos.values()}) 

                # 2. Adiciona usuários base (Admin/Secretaria)
                for login, user in data.get('usuarios', {}).items():
                    self.usuarios[login] = user
                
            print(f"[INFO] Dados carregados de {ARQUIVO_DADOS} com sucesso.")
            
            # Garante que o admin/secretaria padrão estejam sempre presentes
            if 'admin' not in self.usuarios:
                 self.usuarios['admin'] = Usuario('admin', '123', 'Admin Master', 'administrador')
                 self.usuarios['secretaria1'] = Usuario('secretaria1', '123', 'Ana Secretária', 'secretaria')
                 print("[AVISO] Usuários iniciais (admin/secretaria) recriados em memória.")


        except Exception as e:
            print(f"[ERRO] Falha ao carregar dados: {e}. Iniciando com dados padrão.")
            self.carregar_dados_iniciais()


    def matricular_aluno(self, ra, id_disciplina):
        aluno = self.alunos.get(ra)
        disciplina = self.disciplinas.get(id_disciplina)

        if aluno and disciplina and ra not in disciplina.alunos_ra:
            disciplina.alunos_ra.append(ra)
            aluno.cursos[id_disciplina] = {'status': 'Matriculado'}
            self.salvar_dados() 
            return True
        return False
        
    def cancelar_matricula(self, ra, id_disciplina):
        aluno = self.alunos.get(ra)
        disciplina = self.disciplinas.get(id_disciplina)

        if not aluno:
            return False, "Aluno não encontrado."
        if not disciplina:
            return False, "Disciplina não encontrada."
        if id_disciplina not in aluno.cursos:
            return False, "Aluno não está matriculado nesta disciplina."

        # 1. Remover do aluno (curso, frequências e notas)
        del aluno.cursos[id_disciplina]
        if id_disciplina in aluno.frequencias:
            del aluno.frequencias[id_disciplina]
        if id_disciplina in aluno.notas:
            del aluno.notas[id_disciplina]

        # 2. Remover da disciplina (lista de alunos_ra)
        if ra in disciplina.alunos_ra:
            disciplina.alunos_ra.remove(ra)
            
        self.salvar_dados() 
        return True, "Matrícula cancelada com sucesso."

# --- Funções de Menu (Lógica de Interação)

def exibir_menu(perfil):
    # Exibe o menu de acordo com o perfil do usuário
    print(f"\n--- Menu Principal ({perfil.upper()}) ---")
    if perfil == 'administrador':
        print("1. Gerenciar Usuários (Criar/Consultar)")
        print("2. Gerenciar Disciplinas (Criar/Atribuir Professor)")
        print("3. CANCELAR MATRÍCULA de Aluno") 
    elif perfil == 'secretaria':
        print("1. Cadastrar Aluno")
        print("2. Cadastrar Professor")
        print("3. Gerenciar Matrículas (Aluno em Disciplina)")
        print("4. Listar Alunos e Professores")
        print("5. CANCELAR MATRÍCULA de Aluno") 
    elif perfil == 'professor':
        print("1. Consultar Minhas Turmas e Alunos")
        print("2. Lançar Notas")
        print("3. Registrar Frequências")
    elif perfil == 'aluno':
        print("1. Realizar Matrícula em Disciplina")
        print("2. Consultar Notas e Média")
        print("3. Consultar Frequência")
        print("4. Atualizar Dados Pessoais")
        print("5. Emitir Histórico Escolar")
    print("0. Sair / Fazer Logout")
    return input("Escolha uma opção: ")

# FUNÇÃO AUXILIAR PARA CANCELAR MATRÍCULA (Reutilizável)
def logica_cancelar_matricula(sistema):
    print("\n[Admin/Secretaria] Cancelar matrícula de Aluno")
    ra = input("RA do aluno para cancelar a matrícula: ")
    disciplina_id = input("ID da disciplina para cancelar a matrícula: ")

    sucesso, mensagem = sistema.cancelar_matricula(ra, disciplina_id)
    if sucesso:
        print(f"SUCESSO: {mensagem} (RA: {ra}, Disciplina: {disciplina_id})")
    else:
        print(f"ERRO: {mensagem}")


# --- Perfis

def menu_administrador(sistema):
    while True:
        opcao = exibir_menu('administrador')
        if opcao == '1':
            print("\n[Admin] Criar Novo Usuário")
            login = input("Login: ")
            if login in sistema.usuarios:
                print("ERRO: Login já existe.")
                continue
            senha = input("Senha: ")
            nome = input("Nome: ")
            perfil = input("Perfil (secretaria/professor/aluno/administrador): ").lower()
            
            if perfil == 'aluno':
                ra = input("RA do aluno: ")
                
                novo_usuario = Aluno(login, senha, nome, ra)
                sistema.alunos[ra] = novo_usuario
            elif perfil == 'professor':
                
                novo_usuario = Professor(login, senha, nome)
                sistema.professores[login] = novo_usuario
            elif perfil in ['secretaria', 'administrador']:
                novo_usuario = Usuario(login, senha, nome, perfil)
            else:
                print("ERRO: Perfil inválido.")
                continue
            
            sistema.usuarios[login] = novo_usuario
            print(f"Usuário {nome} ({perfil.upper()}) criado com sucesso.")
            sistema.salvar_dados() 
            
        elif opcao == '2':
            print("\n[Admin] Gerenciar Disciplinas")
            id_disc = input("ID da nova disciplina (Ex: PORT101): ")
            if id_disc in sistema.disciplinas:
                print("ERRO: Disciplina já existe.")
                continue

            nome_disc = input("Nome da disciplina: ")
            prof_login = input("Login do professor para atribuir (deixe vazio para sem atribuição): ")
            
            if prof_login and prof_login in sistema.professores:
                disciplina = Disciplina(id_disc, nome_disc, prof_login)
                sistema.professores[prof_login].disciplinas_ministradas.append(id_disc)
                print(f"Disciplina {nome_disc} criada e atribuída a {prof_login}.")
            elif prof_login and prof_login not in sistema.professores:
                 disciplina = Disciplina(id_disc, nome_disc)
                 print(f"AVISO: Professor {prof_login} não encontrado. Disciplina criada sem atribuição.")
            else:
                 disciplina = Disciplina(id_disc, nome_disc)
                 print(f"Disciplina {nome_disc} criada. Professor não atribuído.")

            sistema.disciplinas[id_disc] = disciplina
            sistema.salvar_dados() 

        elif opcao == '3':
            logica_cancelar_matricula(sistema)

        elif opcao == '0':
            break
        else:
            print("Opção inválida.")

def menu_secretaria(sistema):
    while True:
        opcao = exibir_menu('secretaria')
        if opcao == '1':
            print("\n[Secretaria] Cadastrar Aluno (Criar Usuário e Objeto Aluno)")
            login = input("Login para o aluno: ")
            if login in sistema.usuarios:
                print("ERRO: Login já existe.")
                continue
            ra = input("RA do novo aluno: ")
            if ra in sistema.alunos:
                print("ERRO: RA já cadastrado.")
                continue
            nome = input("Nome do aluno: ")
            senha = input("Senha inicial: ")
            
            novo_aluno = Aluno(login, senha, nome, ra)
            sistema.usuarios[login] = novo_aluno
            sistema.alunos[ra] = novo_aluno
            print(f"Aluno {nome} (RA: {ra}) cadastrado com sucesso.")
            sistema.salvar_dados() 

        elif opcao == '2':
            print("\n[Secretaria] Cadastrar Professor (Criar Usuário e Objeto Professor)")
            login = input("Login do novo professor: ")
            if login in sistema.usuarios:
                print("ERRO: Login já existe.")
                continue
            nome = input("Nome do professor: ")
            senha = input("Senha inicial: ")
         
            novo_professor = Professor(login, senha, nome)
            sistema.usuarios[login] = novo_professor
            sistema.professores[login] = novo_professor
            print(f"Professor {nome} (Login: {login}) cadastrado com sucesso.")
            sistema.salvar_dados() 

        elif opcao == '3':
            print("\n[Secretaria] Gerenciar Matrículas")
            ra = input("RA do aluno a matricular: ")
            disciplina_id = input("ID da disciplina (Ex: MAT101): ")

            if ra not in sistema.alunos:
                print("ERRO: Aluno não encontrado.")
            elif disciplina_id not in sistema.disciplinas:
                print("ERRO: Disciplina não encontrada.")
            elif ra in sistema.disciplinas.get(disciplina_id, {}).alunos_ra:
                print("ERRO: Aluno já matriculado nesta disciplina.")
            else:
                if sistema.matricular_aluno(ra, disciplina_id):
                    print(f"Aluno {ra} matriculado na disciplina {disciplina_id} com sucesso.")
                else:
                    print("ERRO: Falha na matrícula.")
            
        elif opcao == '4':
            print("\n[Secretaria] Listagem de Cadastros:")
            print(f"--- ALUNOS ({len(sistema.alunos)}) ---")
            for ra, aluno in sistema.alunos.items():
                print(f"RA: {ra} | Nome: {aluno.nome}")
            print(f"\n--- PROFESSORES ({len(sistema.professores)}) ---")
            for login, prof in sistema.professores.items():
                print(f"Login: {login} | Nome: {prof.nome} | Disciplinas: {', '.join(prof.disciplinas_ministradas) if prof.disciplinas_ministradas else 'Nenhuma'}")
            print(f"\n--- DISCIPLINAS ({len(sistema.disciplinas)}) ---")
            for id_disc, disc in sistema.disciplinas.items():
                 prof_nome = sistema.professores.get(disc.professor_login).nome if disc.professor_login in sistema.professores else 'Não Atribuído'
                 print(f"ID: {id_disc} | Nome: {disc.nome} | Professor: {prof_nome} | Alunos: {len(disc.alunos_ra)}")


        elif opcao == '5':
            logica_cancelar_matricula(sistema)
            
        elif opcao == '0':
            break
        else:
            print("Opção inválida.")

def menu_professor(sistema, usuario_logado):
    professor = sistema.professores.get(usuario_logado.login)
    if not professor:
          print("ERRO: Usuário logado não é um professor válido no sistema.")
          return

    while True:
        opcao = exibir_menu('professor')
        
        if opcao == '1':
            print(f"\n[Professor] Minhas Turmas e Alunos:")
            if not professor.disciplinas_ministradas:
                print("Nenhuma disciplina atribuída.")
                continue

            for disc_id in professor.disciplinas_ministradas:
                disciplina = sistema.disciplinas.get(disc_id)
                if not disciplina:
                      print(f"AVISO: Disciplina ID {disc_id} não encontrada no sistema.")
                      continue
                      
                alunos_ra = disciplina.alunos_ra
                print(f"\n--- Disciplina: {disciplina.nome} ({disc_id}) ---")
                if alunos_ra:
                    for ra in alunos_ra:
                        aluno = sistema.alunos.get(ra)
                        if aluno:
                           print(f" - RA: {aluno.ra} - Nome: {aluno.nome}")
                        else:
                           print(f" - RA: {ra} - Nome: (Aluno não encontrado)")
                else:
                    print("Nenhum aluno matriculado.")

        elif opcao == '2':
            print("\n[Professor] Lançar Notas")
            disc_id = input("ID da disciplina: ")
            if disc_id not in professor.disciplinas_ministradas:
                print("ERRO: Disciplina não encontrada ou não atribuída a você.")
                continue
            
            ra = input("RA do aluno: ")
            aluno = sistema.alunos.get(ra)
            if not aluno or ra not in sistema.disciplinas[disc_id].alunos_ra:
                print("ERRO: Aluno não encontrado ou não matriculado nesta turma.")
                continue

            try:
                nova_nota = float(input("Digite a nova nota (0.0 a 10.0): "))
                if 0.0 <= nova_nota <= 10.0:
                    if disc_id not in aluno.notas:
                        aluno.notas[disc_id] = []
                    
                    aluno.notas[disc_id].append(nova_nota)
                    media_atual = aluno.calcular_media(disc_id)
                    print(f"Nota {nova_nota} lançada. Média atual: {media_atual:.2f}")
                    sistema.salvar_dados() 
                else:
                    print("ERRO: Nota deve estar entre 0.0 e 10.0.")
            except ValueError:
                print("ERRO: Entrada inválida. Digite um número.")

        elif opcao == '3':
            print("\n[Professor] Registrar Frequências")
            disc_id = input("ID da disciplina: ")
            if disc_id not in professor.disciplinas_ministradas:
                print("ERRO: Disciplina não encontrada ou não atribuída a você.")
                continue
            
            disciplina = sistema.disciplinas[disc_id]
            data_aula = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Registrando frequência para aula ({data_aula}):")

            if not disciplina.alunos_ra:
                print("Nenhum aluno matriculado nesta disciplina.")
                continue

            frequencia_registrada = False
            for ra in disciplina.alunos_ra:
                aluno = sistema.alunos.get(ra)
                if not aluno:
                    continue 
                while True:
                    freq = input(f"Aluno {aluno.nome} ({ra}) - Presença (P) ou Falta (F)? ").upper()
                    if freq in ['P', 'F']:
                        if disc_id not in aluno.frequencias:
                            aluno.frequencias[disc_id] = []
                        
                        aluno.frequencias[disc_id].append({'data': data_aula, 'tipo': freq})
                        print(f"Frequência registrada: {freq}")
                        frequencia_registrada = True
                        break
                    else:
                        print("Entrada inválida.")
            
            if frequencia_registrada:
                sistema.salvar_dados() 
                
            print("Registro de frequências concluído.")

        elif opcao == '0':
            break
        else:
            print("Opção inválida.")

def menu_aluno(sistema, aluno):
    while True:
        opcao = exibir_menu('aluno')
        
        if opcao == '1':
            print("\n[Aluno] Realizar Matrícula em Disciplina")
            disc_id = input("ID da disciplina para matricular: ")
            if disc_id not in sistema.disciplinas:
                print("ERRO: Disciplina não encontrada.")
                continue
            
            if disc_id in aluno.cursos:
                print("Você já está matriculado nesta disciplina.")
                continue

            if sistema.matricular_aluno(aluno.ra, disc_id):
                print(f"Matrícula na disciplina {disc_id} realizada com sucesso!")
            else:
                 print("ERRO: Falha na matrícula. Verifique se a disciplina ou seu RA estão corretos.")

        elif opcao == '2':
            print("\n[Aluno] Consultar Notas e Média")
            if not aluno.cursos:
                 print("Você não está matriculado em nenhuma disciplina.")
                 continue

            for disc_id in aluno.cursos.keys():
                situacao, freq_perc, media = aluno.verificar_aprovacao(disc_id)
                notas = aluno.notas.get(disc_id, [])
                
                print(f"\n--- {sistema.disciplinas.get(disc_id, Disciplina(disc_id, 'N/A')).nome} ({disc_id}) ---")
                print(f"Notas Lançadas: {notas if notas else 'Nenhuma'}")
                print(f"Média Final: {media:.2f} ")
                print(f"Situação por Nota: {'APROVADO' if media >= MEDIA_APROVACAO else 'REPROVADO'}")

        elif opcao == '3':
            print("\n[Aluno] Consultar Frequência")
            if not aluno.cursos:
                 print("Você não está matriculado em nenhuma disciplina.")
                 continue

            for disc_id in aluno.cursos.keys():
                situacao, freq_perc, media = aluno.verificar_aprovacao(disc_id)
                frequencias = aluno.frequencias.get(disc_id, [])
                total_aulas = len(frequencias)
                total_presencas = sum(1 for f in frequencias if f['tipo'] == 'P')
                total_faltas = total_aulas - total_presencas
                
                print(f"\n--- {sistema.disciplinas.get(disc_id, Disciplina(disc_id, 'N/A')).nome} ({disc_id}) ---")
                print(f"Aulas Registradas: {total_aulas}")
                print(f"Presenças: {total_presencas} | Faltas: {total_faltas}")
                print(f"Frequência: {freq_perc:.2f}% (Mínimo: {PERCENTUAL_FREQUENCIA_MINIMA}%)")

        elif opcao == '4':
            print("\n[Aluno] Atualizar Dados Pessoais")
            novo_nome = input(f"Nome atual ({aluno.nome}). Novo nome (deixe vazio para manter): ")
            if novo_nome:
                aluno.nome = novo_nome
            
            nova_senha = input("Alterar senha (deixe vazio para manter): ")
            if nova_senha:
                aluno.senha = nova_senha 

            novo_end = input(f"Endereço atual ({aluno.dados_pessoais.get('endereco', 'N/A')}). Novo Endereço: ")
            if novo_end:
                 aluno.dados_pessoais['endereco'] = novo_end

            print("Dados pessoais atualizados com sucesso.")
            sistema.salvar_dados() 

        elif opcao == '5':
            print("\n[Aluno] Emitir Histórico Escolar")
            print(f"--- Histórico Escolar de {aluno.nome} (RA: {aluno.ra}) ---")
            
            if not aluno.cursos:
                 print("Nenhum histórico a emitir, você não está matriculado em nenhuma disciplina.")
                 continue

            aprovacoes = []
            reprovacoes = []

            for disc_id in aluno.cursos.keys():
                situacao, freq_perc, media = aluno.verificar_aprovacao(disc_id)
                
                resultado = {
                    'disciplina': sistema.disciplinas.get(disc_id).nome if sistema.disciplinas.get(disc_id) else "Disciplina Removida",
                    'media': f"{media:.2f}",
                    'frequencia': f"{freq_perc:.2f}%",
                    'status': situacao
                }

                print(f"\nDisciplina: {resultado['disciplina']}")
                print(f"   Média: {resultado['media']} | Frequência: {resultado['frequencia']}")
                print(f"   Situação Final: {resultado['status']}")
                
                if situacao.startswith('REPROVADO'):
                    reprovacoes.append(resultado)
                else:
                    aprovacoes.append(resultado)

            if reprovacoes:
                print("\nSituação Global: PENDÊNCIAS (Verifique reprovações)")
                print(f"Total de reprovações: {len(reprovacoes)}")
            else:
                print("\nSituação Global: REGULAR")

        elif opcao == '0':
            break
        else:
            print("Opção inválida.")

# --- Lógica de Inicialização e Autenticação

def login(sistema):
    print("\n--- Sistema Acadêmico - Login ---")
    usuario = input("Login: ")
    senha = input("Senha: ")

    usuario_logado = sistema.usuarios.get(usuario)

    if usuario_logado and usuario_logado.senha == senha:
        perfil = usuario_logado.perfil
        print(f"Login bem-sucedido! Perfil: {perfil.upper()}")
        
        # Chama o menu específico
        if perfil == 'administrador':
            menu_administrador(sistema)
        elif perfil == 'secretaria':
            menu_secretaria(sistema)
        elif perfil == 'professor':
            menu_professor(sistema, usuario_logado)
        elif perfil == 'aluno':
            aluno_obj = sistema.alunos.get(usuario_logado.ra)
            if aluno_obj:
                menu_aluno(sistema, aluno_obj)
            else:
                # O objeto Aluno é referenciado pelo RA
                print("ERRO interno: Objeto Aluno não encontrado. Verifique se o RA está cadastrado.")

        print(f"Logout realizado.")
    else:
        print("Login ou senha incorretos.")

# --- Execução Principal
if __name__ == "__main__":
    sistema = SistemaAcademico() 

    while True:
        login(sistema)
        continuar = input("\nPressione Enter para tentar outro login ou 'q' para encerrar: ").lower()
        if continuar == 'q':
            sistema.salvar_dados() # Salva o estado final antes de sair
            print("Sistema acadêmico simulado encerrado.")
            break