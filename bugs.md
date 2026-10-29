### 📩 Mensagem para a Mikaelle e o Agente:                                                                                                           
                                                                                                                                                        
    Oi Mikaelle! Seu PR e as implementações em `app.py` ficaram excelentes: o controle de concorrência com `RLock`, o isolamento dos visitantes em      
  memória, a sanitização e o padrão PRG estão funcionando muito bem.                                                                                    
                                                                                                                                                        
    Fizemos uma revisão no código da sua branch `feat/Mikaelle-implementacao-app.py` e identificamos apenas 4 ajustes pontuais (sendo 1 bug crítico na  
  rota de criação e 3 melhorias de tipagem/segurança). Segue a especificação para você ou seu agente ajustarem em `app.py`:                             
                                                                                                                                                        
    ---                                                                                                                                                 
                                                                                                                                                        
    ### 1. 🚨 [Bug Crítico] Correção do desempacotamento de `buscar_coordenadas` em `/viagens/criar`                                                    
    - **Onde:** app.py na rota `def criar_viagem()`.                                                                                                    
    - **Problema:** A função `buscar_coordenadas(client, cidade, uf)` do `services.py` retorna a tupla `(latitude, longitude, uf_oficial_detectada)`. O 
  3º valor retornado é apenas a **sigla da UF** (ex: `'PI'`, `'DF'`), e não o nome da cidade. Atualmente o código está salvando `"origem": nome_origem` 
  (que fica `"PI"` em vez de `"Teresina - PI"`), o link do Maps fica quebrado (`origin=PI`) e a IA do Gemini recebe apenas `"DF"` como destino. Além    
  disso, o campo `geolocalizacao.origem.uf` precisa usar a UF corrigida pelo geocoding.                                                                 
    - **Como corrigir:**                                                                                                                                
    Substitua o trecho de desempacotamento e montagem de nomes por:                                                                                     
    ```python                                                                                                                                           
            with httpx.Client() as client:                                                                                                              
                lat_origem, lon_origem, uf_origem_det = buscar_coordenadas(                                                                             
                    client,                                                                                                                             
                    origem_cidade,                                                                                                                      
                    origem_uf,                                                                                                                          
                )                                                                                                                                       
                                                                                                                                                        
                lat_destino, lon_destino, uf_destino_det = buscar_coordenadas(                                                                          
                    client,                                                                                                                             
                    destino_cidade,                                                                                                                     
                    destino_uf,                                                                                                                         
                )                                                                                                                                       
                                                                                                                                                        
                # Garante o uso da UF real detectada pelo Geocoding (ex: Teresina / RJ -> corrigido para PI)                                            
                uf_origem_final = uf_origem_det or origem_uf                                                                                            
                uf_destino_final = uf_destino_det or destino_uf                                                                                         
                                                                                                                                                        
                nome_origem = f"{origem_cidade} - {uf_origem_final}"                                                                                    
                nome_destino = f"{destino_cidade} - {uf_destino_final}"                                                                                 
                                                                                                                                                        
  E no dicionário viagem, atualize os nós de geolocalização para usarem as UFs finais:                                                                  
                                                                                                                                                        
                    "origem": nome_origem,                                                                                                              
                    "destino": nome_destino,                                                                                                            
                    "geolocalizacao": {                                                                                                                 
                        "origem": {                                                                                                                     
                            "cidade": origem_cidade,                                                                                                    
                            "uf": uf_origem_final,                                                                                                      
                            "latitude": lat_origem,                                                                                                     
                            "longitude": lon_origem,                                                                                                    
                        },                                                                                                                              
                        "destino": {                                                                                                                    
                            "cidade": destino_cidade,                                                                                                   
                            "uf": uf_destino_final,                                                                                                     
                            "latitude": lat_destino,                                                                                                    
                            "longitude": lon_destino,                                                                                                   
                        },                                                                                                                              
                    },                                                                                                                                  
  ──────                                                                                                                                                
  ### 2. 🛡️ [Defensividade] Tratamento para funções externas ainda em desenvolvimento                                                                   
                                                                                                                                                        
  • Onde: app.py dentro de criar_viagem().                                                                                                              
  • Problema: Como as funções obter_guia_destino_com_diagnostico, obter_clima e obter_percurso do Aluno 2 ainda podem estar com pass ou retornar None, a
  linha dicas_destino, diagnostico_ia = obter_guia_destino_com_diagnostico(...) dispara TypeError: cannot unpack non-iterable NoneType object.          
  • Como corrigir:                                                                                                                                      
  Adicione fallbacks defensivos:                                                                                                                        
                                                                                                                                                        
                clima_destino = obter_clima(                                                                                                            
                    client,                                                                                                                             
                    lat_destino,                                                                                                                        
                    lon_destino,                                                                                                                        
                ) or {"temperatura": "N/D", "umidade": "N/D", "vento": "N/D"}                                                                           
                                                                                                                                                        
                percurso = obter_percurso(                                                                                                              
                    client,                                                                                                                             
                    lat_origem,                                                                                                                         
                    lon_origem,                                                                                                                         
                    lat_destino,                                                                                                                        
                    lon_destino,                                                                                                                        
                ) or {"distancia": "N/D", "tempo": "N/D", "modal": "carro"}                                                                             
                                                                                                                                                        
                res_ia = obter_guia_destino_com_diagnostico(nome_destino)                                                                               
                if isinstance(res_ia, tuple) and len(res_ia) == 2:                                                                                      
                    dicas_destino, diagnostico_ia = res_ia                                                                                              
                else:                                                                                                                                   
                    dicas_destino = str(res_ia or "Guia temporariamente indisponível.")                                                                 
                    diagnostico_ia = {"status": "fallback", "fallback": True}                                                                           
  ──────                                                                                                                                                
  ### 3. ⚡ [MyPy] Resolução dos avisos de tipagem estática nas linhas 123, 224 e 284                                                                   
                                                                                                                                                        
  • Onde: Funções salvar_dados_viagens_json, adicionar_viagem_usuario e remover_viagem_usuario.                                                         
  • Problema: dados_completos["total_roteiros"] = sum(len(u.get("roteiros", u.get("viagens", []))) ...) causa o erro Generator has incompatible item    
  type "int"; expected "bool" no MyPy e pode quebrar em runtime caso o valor retornado seja None.                                                       
  • Como corrigir:                                                                                                                                      
  Em salvar_dados_viagens_json:                                                                                                                         
                                                                                                                                                        
            usuarios = dados_completos.get("usuarios")                                                                                                  
            if isinstance(usuarios, dict):                                                                                                              
                dados_completos["usuarios"] = {                                                                                                         
                    uid: uinfo                                                                                                                          
                    for uid, uinfo in usuarios.items()                                                                                                  
                    if not eh_usuario_visitante(                                                                                                        
                        uid,                                                                                                                            
                        uinfo.get("perfil") if isinstance(uinfo, dict) else None,                                                                       
                    )                                                                                                                                   
                }                                                                                                                                       
                dados_completos["total_usuarios"] = len(dados_completos["usuarios"])                                                                    
                                                                                                                                                        
                total_roteiros = 0                                                                                                                      
                for u in dados_completos["usuarios"].values():                                                                                          
                    if isinstance(u, dict):                                                                                                             
                        roteiros_u = u.get("roteiros") or u.get("viagens")                                                                              
                        if isinstance(roteiros_u, list):                                                                                                
                            total_roteiros += len(roteiros_u)                                                                                           
                dados_completos["total_roteiros"] = total_roteiros                                                                                      
                                                                                                                                                        
  (Nota: em adicionar_viagem_usuario e remover_viagem_usuario, o cálculo redundante de dados["total_roteiros"] antes de chamar                          
  salvar_dados_viagens_json(dados) pode ser removido, pois o salvar já recalcula de forma centralizada).                                                
  ──────                                                                                                                                                
  ### 4. 🔄 [Refatoração] Unificar verificação de visitante                                                                                             
                                                                                                                                                        
  • Onde: Função _obter_roteiros_visitante_ativo() em app.py.                                                                                           
  • Problema: Hoje ela faz if not user_id.startswith(("visitante_", "visitante-")): return None.                                                        
  • Como corrigir:                                                                                                                                      
  Reaproveite a função que você mesma criou (eh_usuario_visitante):                                                                                     
                                                                                                                                                        
    def _obter_roteiros_visitante_ativo() -> tuple[str, list[dict[str, Any]]] | None:                                                                   
        usuario = session.get("usuario")                                                                                                                
        if not usuario or not isinstance(usuario, dict):                                                                                                
            return None                                                                                                                                 
                                                                                                                                                        
        user_id = str(usuario.get("id", ""))                                                                                                            
        if not eh_usuario_visitante(user_id, usuario):                                                                                                  
            return None                                                                                                                                 
                                                                                                                                                        
        with lock_arquivo_json:                                                                                                                         
            roteiros = viagens_visitante_memoria.get(user_id, [])                                                                                       
            if not roteiros:                                                                                                                            
                return None                                                                                                                             
                                                                                                                                                        
            return user_id, list(roteiros)                                                                                                              
  ──────                                                                                                                                                
  Feitos esses 4 ajustes, rode ruff check app.py e mypy app.py para garantir que passam 100% sem erros!