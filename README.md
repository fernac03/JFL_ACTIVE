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

## Instalação via HACS

[![Abrir seu Home Assistant instance e abrir um repositório dentro do Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=fernac03&repository=JFL_ACTIVE&category=integration)

## Instalação manual

Copie o conteúdo deste repositório para a pasta `/config/custom_components/jfl_active`.

## Configuração

1. Configure a integração com o ip e portas que estará houvindo a central JFL
2. Configure a central para enviar o report via ethernet para o ip e porta que foi configurado a integração
   - Na Active 20 ethernet IP de destino (endereços 702 e 703) e a porta de destino (endereços 706 e 707):


3. Defina uma senha para o alarme, não precisa ser a mesma da central
4. Configure as zonas

## Funções

Desarme  -  Desarma as  duas  Partições<br>
Arme Away (Armar Ausente )  Arma as duas Partiçoes<br>
Arme Home (Armar em Casa)  Arma  apenas a primeira particao<br>
Arme Night (Armar a Noite)  Arma  as duas partições<br>
