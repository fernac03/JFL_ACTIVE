# JFL Active

Integração com o Home Assistant para as centrais de alarme JFL da linha Active.

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
