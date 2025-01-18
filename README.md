# JFL Active

Integração com o Home Assistant para as centrais de alarme JFL da linha Active.

# Centrais  Suportadas  pela  Integração 

Active 8 Ultra     Placa:PCI-327  Firmare: A partir de 6.0

Active 20 Ultra    Placa:PCI-327  Firmare: A partir de 6.0

Active 20 Ethernet Placa:PCI-340      Firmare:A partir de 6.0

Active 20 Bus      Placa:PCI-358      Firmare:Todas

Active 32 Duo      Placa:PCI-356      Firmare:A partir de 5.0

Active 100 Bus     Placa:PCI-350      Firmare:Todas

Active Full 32     Placa:PCI-444      Firmare:Todas

Active 20          Placa:PCI-325      Firmare:Todas

Active 8W          Placa:Todas        Firmare:Todas


# Modulos
M-300+            Placa:Todas        Firmare:Todas
M-300 Flex        Placa:Todas        Firmare:Todas

# DIFERENÇAS BÁSICAS DOS MODELOS DE CENTRAIS DE ALARME

 Active 8 Ultra:
• 2 Partições.
• 12 Zonas.
• Não possui PGM.
• Não possui controle de eletrificador

Active 20 Bus:
• 2 Partições.
• 32 Zonas.
• 16 PGM.
• Controle de eletrificador.

Active 20 Ultra, Active 20 Ethernet e Active 20 GPRS:
• 2 Partições.
• 22 Zonas.
• 4 PGM.
• Controle de eletrificador.

Active 32 Duo:
• 4 Partições.
• 32 Zonas.
• 4 PGM.
• Controle de eletrificador.

Active 100 Bus:
• 16 Partições.
• 99 Zonas.
• 16 PGM.
• Controle de eletrificador.

Active Full 32:
• 4 Partições.
• 32 Zonas.
• 16 PGM.
• Não possui controle de eletrificador.

Active 20:
• 2 Partições.
• 32 Zonas.
• 4 PGM.
• Controle de eletrificador

Active 8W:
 • 2 Partições.
 • 32 Zonas.
 • 4 PGM.
 • Controle de eletrificador.

M-300 +:
 • 2 PGM.
 • 2 Entradas.

M-300 Flex:
 • 2 PGM.
 • 2 Entradas.

## Instalação via HACS

[![Abrir seu Home Assistant instance e abrir um repositório dentro do Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=fernac03&repository=JFL_ACTIVE&category=integration)

## Instalação manual

Copie o conteúdo deste repositório para a pasta `/config/custom_components/jfl_active`.

## Configuração

1. Configure a integração com o ip do HA (não utilize localhost) e porta livre no seu sistema a  central JFL ira se conectar neste ip e porta.
2. Configure a central para enviar o report via ethernet para o ip e porta que foi configurado a integração
   - Na Active 20 ethernet IP de destino (endereços 702 e 703) e a porta de destino (endereços 706 e 707):
   - no configurador Active net use a Aba Comunicação e configure o ip do software active Net como sendo o ip do HA  e a porta configurada
   ![image](https://github.com/user-attachments/assets/5881fba8-20d9-4a24-982b-9d7662d4b31b)


  - no configurador Mobile vá  em  comunicação -> ip destino 1  coloque o IP do HA e porta destino 1  coloca a porta  cadastrada  
  exemplos: 192.168.1.1  porta 8085

3. Apos  Reiniciar  o HA  abra  a integração e  faça  a configuração do Arming Settings
  ![image](https://github.com/user-attachments/assets/e862150b-44f0-48c3-8c72-02b93380a6d4)

4. Defina uma senha para o alarme, não precisa ser a mesma da central
 ![image](https://github.com/user-attachments/assets/f2b62ce6-c89f-4185-bc8d-0377b33a7229)

4. Configure as zonas
![image](https://github.com/user-attachments/assets/5c932bea-bd00-48d3-9c37-521329a920e2)
![image](https://github.com/user-attachments/assets/b52e7615-bdd7-436a-a6b5-85e48599aa12)
coloque  a numerração de zonas  de acordo  com as zonas  no APP Mobile  da JFL


## Funções

Desarme  -  Desarma as  duas  Partições<br>
Arme Away (Armar Ausente )  Arma as duas Partiçoes<br>
Arme Home (Armar em Casa)  Arma  apenas a primeira particao<br>
Arme Night (Armar a Noite)  Arma  as duas partições<br>
