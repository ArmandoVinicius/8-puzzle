# -*- coding: utf-8 -*-
from pysat.solvers import Minisat22
import copy
import random

PUZZLE_SIZE = 3
NUMBER_OF_PIECES = PUZZLE_SIZE * PUZZLE_SIZE
DIRECTIONS = {'C': (-1,0), 'B': (1,0), 'E': (0,-1), 'D': (0,1)}  # Cima, Baixo, Esquerda, Direita

GOAL_STATE = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8]
]

def puzzle_repr(state):
  for line in state:
    print(' '.join(str(x) if x > 0 else ' ' for x in line))
  print('')

def get_positions():
  return [(i, j) for i in range(PUZZLE_SIZE) for j in range(PUZZLE_SIZE)]

def generate_var_map(N):
  var_map = dict()
  inverse_map = dict()
  current_id = 1
  for s in range(1, N+2):
    for i in range(PUZZLE_SIZE):
      for j in range(PUZZLE_SIZE):
        for k in range(NUMBER_OF_PIECES):
          key = f'{s}_P_{i}_{j}_{k}'
          var_map[key] = current_id
          inverse_map[current_id] = key
          current_id += 1

  for s in range(1, N+1):
    for direction in DIRECTIONS:
      key = f'{s}_A_{direction}'
      var_map[key] = current_id
      inverse_map[current_id] = key
      current_id += 1
  return var_map, inverse_map

def shuffle_state(state, movements=10):
  print(movements, "movimentos de embaralhamento")
  while True:
    current = copy.deepcopy(state)

    zero_pos = [(i, j) for i in range(PUZZLE_SIZE) for j in range(PUZZLE_SIZE) if current[i][j] == 0][0]
    last = None
    for _ in range(movements):
      i, j = zero_pos
      possible_moves = []
      for d, (di, dj) in DIRECTIONS.items():
        ni, nj = i+di, j+dj
        if 0 <= ni < PUZZLE_SIZE and 0 <= nj < PUZZLE_SIZE and (last is None or (ni, nj) != last):
            possible_moves.append((ni, nj))
      if not possible_moves:
        break
      ni, nj = random.choice(possible_moves)
      current[i][j], current[ni][nj] = current[ni][nj], current[i][j]
      last = (i, j)
      zero_pos = (ni, nj)
    if is_solvable(current):
      return current

def is_solvable(state):
    lst = [x for line in state for x in line if x != 0]
    inversions = sum(
        1
        for i in range(len(lst))
        for j in range(i+1, len(lst))
        if lst[i] > lst[j]
    )
    return inversions % 2 == 0

def add_position_rules(s, var_map, clauses):
  # Só uma peça por posição (se o 3 estiver no (1, 1), não pode haver outra peça no (1, 1) no mesmo passo)
  for i, j in get_positions():
    vars_pos = [var_map[f'{s}_P_{i}_{j}_{k}'] for k in range(NUMBER_OF_PIECES)]
    for x in range(NUMBER_OF_PIECES):
      for y in range(x+1, NUMBER_OF_PIECES):
        clauses.append([-vars_pos[x], -vars_pos[y]])
    clauses.append(vars_pos)

  # Cada peça só em uma posição (se o 2 estiver na posição (1, 1), não pode estar em (0, 0) no mesmo passo)
  for k in range(NUMBER_OF_PIECES):
    vars_peca = [var_map[f'{s}_P_{i}_{j}_{k}'] for i, j in get_positions()]
    for x in range(len(vars_peca)):
      for y in range(x+1, len(vars_peca)):
        clauses.append([-vars_peca[x], -vars_peca[y]])
    clauses.append(vars_peca)

def add_initial_state(state, var_map, clauses):
  for i in range(PUZZLE_SIZE):
    for j in range(PUZZLE_SIZE):
      k = state[i][j]
      clauses.append([var_map[f'1_P_{i}_{j}_{k}']])

def add_final_state(var_map, clauses, N):
  for i in range(PUZZLE_SIZE):
    for j in range(PUZZLE_SIZE):
      k = GOAL_STATE[i][j]
      clauses.append([var_map[f'{N+1}_P_{i}_{j}_{k}']])

def add_one_action_per_step(N, var_map, clauses):
  for s in range(1, N+1):
    vars_acao = [var_map[f'{s}_A_{d}'] for d in DIRECTIONS]
    # Pelo menos uma ação
    clauses.append(vars_acao)
    # No máximo uma ação
    for i in range(len(vars_acao)):
      for j in range(i+1, len(vars_acao)):
        clauses.append([-vars_acao[i], -vars_acao[j]])

def add_transitions(N, var_map, clauses):
  for s in range(1, N+1):
    for i in range(PUZZLE_SIZE):
      for j in range(PUZZLE_SIZE):
        for direcao, (di, dj) in DIRECTIONS.items():
          ni, nj = i + di, j + dj
          if 0 <= ni < PUZZLE_SIZE and 0 <= nj < PUZZLE_SIZE:
            a = var_map[f"{s}_A_{direcao}"]
            # Para cada peça p (exceto o vazio), se ação tomada, troque (i,j)<->(ni,nj) EXPLICAÇÃO
            # 1. O vazio vai para (ni, nj)
            #2. A peça p vai para (i, j)
            # 3. Todas as outras peças permanecem no mesmo lugar
            #4 . O vazio não pode estar em (ni, nj) se a ação não for tomada
            #5. A peça p não pode estar em (i, j) se a ação não for tomada
            for p in range(1, NUMBER_OF_PIECES):
              preconds = [
                -a,
                -var_map[f"{s}_P_{i}_{j}_0"],      # vazio em (i,j)
                -var_map[f"{s}_P_{ni}_{nj}_{p}"],  # peça p em (ni,nj)
              ]
              # 1. O vazio vai para (ni, nj)
              clauses.append(preconds + [var_map[f"{s+1}_P_{ni}_{nj}_0"]])
              # 2. A peça p vai para (i, j)
              clauses.append(preconds + [var_map[f"{s+1}_P_{i}_{j}_{p}"]])
              # 3. Todas as outras peças permanecem no mesmo lugar
              for x in range(PUZZLE_SIZE):
                for y in range(PUZZLE_SIZE):
                  if (x, y) != (i, j) and (x, y) != (ni, nj):
                    for k in range(NUMBER_OF_PIECES):
                      clauses.append(preconds + [
                        -var_map[f"{s}_P_{x}_{y}_{k}"],
                        var_map[f"{s+1}_P_{x}_{y}_{k}"]
                      ])

# Função que reforça o vazio, ISTO É, garante que só haja um vazio no tabuleiro
def reinforce_empty_space(s, mapa, clausulas):
    vazio_vars = [mapa[f"{s}_P_{i}_{j}_0"] for i, j in get_positions()]
    # Só um vazio no tabuleiro
    for x in range(len(vazio_vars)):
        for y in range(x+1, len(vazio_vars)):
            clausulas.append([-vazio_vars[x], -vazio_vars[y]])
    clausulas.append(vazio_vars)

def add_position_restrictions_for_actions(N, var_map, clauses):
  for s in range(1, N+1):
    for direction, (di, dj) in DIRECTIONS.items():
      var_action = var_map[f'{s}_A_{direction}']
      possible = []
      for i in range(PUZZLE_SIZE):
        for j in range(PUZZLE_SIZE):
          ni, nj = i + di, j + dj
          if 0 <= ni < PUZZLE_SIZE and 0 <= nj < PUZZLE_SIZE:
            # Só possível mover nesta direção se o vazio está em (i, j)
            possible.append(var_map[f'{s}_P_{i}_{j}_0'])
      # Se a ação for escolhida, o vazio deve estar em alguma posição que permite isso
      clauses.append([-var_action] + possible)

# Adiciona o estado final (meta) ao conjunto de cláusulas (utilizado no debug)
def add_final_state(var_map, clauses, N):
  for i in range(PUZZLE_SIZE):
    for j in range(PUZZLE_SIZE):
      k = GOAL_STATE[i][j]
      clauses.append([var_map[f'{N+1}_P_{i}_{j}_{k}']])

# Função principal que resolve o 8-puzzle usando SAT solving
# estado_inicial: estado inicial do puzzle, N_MAX: número máximo de passos a serem tentados
def resolver_8puzzle(estado_inicial, N_MAX=30):
  if estado_inicial == GOAL_STATE:
    return []
  if not is_solvable(estado_inicial):
    print("Este estado não tem solução!")
    return None

  for N in range(1, N_MAX+1):
    print(f"Tentando resolver com {N} movimentos...")
    mapa, inverso = generate_var_map(N)
    clausulas = []

    for s in range(1, N+2):
      add_position_rules(s, mapa, clausulas)
    add_initial_state(estado_inicial, mapa, clausulas)
    add_final_state(mapa, clausulas, N)

    # apenas para depuração
    # print("\nCláusulas de meta (final):")
    # for cl in clausulas[-(PUZZLE_SIZE*PUZZLE_SIZE):]:
    #   print([inverso[v] for v in cl])

    add_one_action_per_step(N, mapa, clausulas)
    add_position_restrictions_for_actions(N, mapa, clausulas)
    add_transitions(N, mapa, clausulas)

    print(f"  Cláusulas: {len(clausulas)}, Variáveis: {len(mapa)}\n")

    with Minisat22(bootstrap_with=clausulas) as m:
      if m.solve():
        modelo = m.get_model()
        modelo_positivo = [x for x in modelo if x > 0]
        acoes = []
        for s in range(1, N+1):
            for d in DIRECTIONS:
                var = mapa[f'{s}_A_{d}']
                if var in modelo_positivo:
                    acoes.append(d)
                    break
        print("Ações encontradas:", acoes)

        caminho = reconstruir_caminho(mapa, inverso, modelo, N)
        for idx, tabuleiro in enumerate(caminho):
            print(f"Passo {idx}:")
            puzzle_repr(tabuleiro)
        return acoes
  print("Não foi possível encontrar solução em", N_MAX, "passos.")
  return None

# Função para reconstruir o caminho, passo a passo
def reconstruir_caminho(mapa, inverso, modelo, N):
  modelo_positivo = [x for x in modelo if x > 0]
  caminho = []
  for s in range(1, N+2):  # de 1 até N+1 (inclui meta)
    tabuleiro = [[-1 for _ in range(PUZZLE_SIZE)] for _ in range(PUZZLE_SIZE)]
    for i in range(PUZZLE_SIZE):
      for j in range(PUZZLE_SIZE):
        for k in range(NUMBER_OF_PIECES):
          var = mapa[f'{s}_P_{i}_{j}_{k}']
          if var in modelo_positivo:
            tabuleiro[i][j] = k
            break  # só pode haver uma peça em cada posição
    caminho.append(tabuleiro)
  return caminho

if __name__ == "__main__":
  quantidade_de_passos = random.randint(1, 15)
  estado_inicial = shuffle_state(GOAL_STATE, movements=quantidade_de_passos)  # pode ajustar movimentos p/ + dificuldade

  print("Estado inicial (aleatório):")
  puzzle_repr(estado_inicial)

  input("Pressione Enter para continuar...")

  print("Buscando solução...")
  acoes = resolver_8puzzle(estado_inicial, N_MAX=15) #sempre tem q ser maior que nr de movimentos do embaralhamento
  if acoes is not None:
    print(f"Solução encontrada em {len(acoes)} movimentos: {acoes}")
    print("Estado inicial:")
    puzzle_repr(estado_inicial)
    print("Estado meta esperado:")
    puzzle_repr(GOAL_STATE)
  else:
    print("Não foi possível encontrar solução.")
