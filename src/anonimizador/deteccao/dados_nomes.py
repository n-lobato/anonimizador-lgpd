"""Listas de apoio para reconhecer nomes de pessoas (já sem acentos, minúsculas).

PRENOMES e SOBRENOMES aumentam a confiança de que uma sequência de palavras
iniciadas em maiúscula é um nome de pessoa. PALAVRAS_COMUNS reúne termos
que aparecem com inicial maiúscula em documentos (cargos, órgãos, lugares,
meses) e que interrompem uma sequência de nome.
"""

PRENOMES = set("""
joao jose antonio francisco carlos paulo pedro lucas luiz luis marcos gabriel rafael daniel
marcelo bruno eduardo felipe filipe raimundo rodrigo manoel manuel mateus matheus andre
fernando fabio leonardo gustavo guilherme leandro tiago thiago anderson ricardo jorge
alexandre roberto sebastiao edson diego vitor victor sergio claudio renato geraldo adriano
luciano julio cesar mario rogerio samuel vinicius alex alan allan arthur artur augusto
benedito bernardo caio cicero cristiano davi david denis diogo douglas edgar edmilson
edivaldo edilson elias emerson enzo erick eric everton fabiano fabricio flavio gilberto
gilmar gilson giovanni giovane henrique heitor hugo igor isaac ivan jair jefferson jeferson
joaquim jonas jonathan jonatas josue juliano kaique kaua kevin leonel lorenzo lourenco luan
marcio marco marcus mauricio mauro miguel milton moises murilo nelson nicolas nicolau nilson
norberto octavio otavio osvaldo oswaldo patrick pietro ramon raul reginaldo reinaldo renan
robson rodolfo romulo ronaldo rubens ruan saulo severino silvio sidney sydney thales tales
thomas tomas tomaz ulisses ulysses valdir valter walter vagner wagner washington wellington
wesley william willian wilson yago iago yuri alcides alberto alfredo almir aloisio altamiro
amaro americo anselmo antenor aparecido ari ariel armando arnaldo baltazar benjamin breno
caetano calebe celso clovis cleber cleiton cleyton cristian damiao danilo dario dionisio
domingos edinaldo edimilson ednaldo edvaldo elton emanuel enrique ernesto evandro expedito
ezequiel fausto feliciano felix firmino franklin frederico gael genival gerson getulio gildo
glauber goncalo hamilton haroldo helio heraldo hermes horacio inacio irineu isaias israel
jacinto jaco jailson janio jeremias joel jociel jordao josias juarez juscelino kleber
laercio lauro lazaro levi lindomar lino lucio ludovico marcelino mariano martim mateo
maximiliano messias michel micael misael natanael nathan natan nestor nilo nivaldo noel
orlando oscar osmar pablo pascoal patricio regis reynaldo rivaldo roberval ronan rui ruy
salomao sandro silas simao tadeu teodoro tobias tulio uriel valdemar valdemir valdeci
vanderlei wanderlei vicente vilmar vladimir wanderley waldir zacarias abel abraao adao
adailton adalberto ademar ademir adilson adolfo agnaldo agostinho aguinaldo ailton airton
alan alcir aldo alexsandro alisson alison almeida amilton anibal antonio apolinario
argemiro aristides arlindo avelino bartolomeu belmiro bento brayan brian carlito cassio
cauã caua cezar claudemir claudionor cleberson clodoaldo crispim custodio dalton davison
deivid deivison denilson derick dimas dionatan djalma dorival durval edenilson edgard
edmar edmundo edu eliel eliseu elizeu elvis emilio erasmo erivaldo esdras estevao eugenio
euclides eurico evaldo everaldo ezio fagner felipe fernandinho flavio florencio gabriel
gaspar genesio germano gervasio gideao gilvan gleison guido haroldo heleno herbert herculano
higor hildebrando hilton humberto iran irani isac italo ivo jadson jaime jairo jander jason
jean jeova jesse jhonatan joacir joaquim jobson jocimar joel johnny jone jose josemar
josivaldo jovino juan juvenal kauan kenedy kennedy lael leo leon leonidas lindberg lourival
luca luciano lucimar lucio luiggi manassés manasses marcony mariano marlon martinho
maximo mikael milton moacir moacyr nathanael nelio nicodemos nilton noe odair odilon olavo
onofre orestes osias osni otacilio otoniel pascal paulino pericles pierre plinio quirino
rafinha ramires renilson ricardo rildo rivelino robert roberio robinson rogerio roney
rony rosivaldo sadi salvio samir sandoval sauro silvano silvestre sinval sivaldo talles
tarcisio teofilo tercio thiago tiburcio ubiratan uelington valdecir valdomiro valmir
vanderson venancio vilson vinicios virgilio wallace walace washington wendel wendell
werner weslley wilker wilton yan yuri zaqueu zeferino zenon
maria ana francisca antonia adriana juliana marcia fernanda patricia aline sandra camila
amanda bruna jessica leticia julia luciana vanessa mariana gabriela vera vitoria larissa
claudia beatriz luana rita sonia renata eliane josefa simone natalia cristina carla debora
rosangela jaqueline jacqueline rosa daniela aparecida marlene terezinha raimunda andreia
andrea fabiana lucia raquel rafaela angela regina sara sarah tatiana alessandra alice
helena laura valentina isabela isabella isabel heloisa lorena livia manuela cecilia sophia
sofia clara yasmin yasmim melissa luiza luisa giovanna giovana lara esther ester rebeca
agatha emanuelly emanuele nicole stella estela bianca carolina caroline priscila priscilla
michele michelle viviane elaine gisele kelly karina karla katia keila lais lidia lilian
luciene lucimara madalena marcela margarida marilia marina marta mirian miriam monica nadia
neide nilza noemi olga paula pamela poliana rosana rosilene rosimeire roseli rute ruth
sabrina samara selma silvia solange suelen sueli talita tamires taina thais tais telma
tereza teresa valeria vania vilma viviana zelia zenaide abigail adelaide adelia adriele
agnes alana alcione alda alicia almerinda alzira amelia anabela andressa angelica anita
antonella arlete augusta aurora barbara benedita betania brenda carmem carmen catarina
celia celina cintia cinthia cleide clarice conceicao cristiane cristiana dalva daiane
dayane denise diana dilma dirce dora doralice dulce edileuza edna eduarda elisa elisabete
elizabete elizabeth eloa eloisa elza emilia erica erika evelyn evelin fatima flavia
gabriele gabrielle geane geisa gilvania gloria graca graziela hilda iara ingrid irene iris
isadora ivone ivete janaina jane joana joice joyce jordana josiane jovana judite julieta
jussara kamila karen kariny lavinia leda leila lena lenita liana lidiane ligia lindalva
lourdes lurdes lucilene luzia mafalda maira maisa marcele margareth mari mariane marlei marli
matilde maura mayara milena mirela nair natali nathalia neusa neuza nivea norma odete
ofelia penelope quiteria regiane rosalia rosemary roberta rosiane salete samanta silmara
sinara socorro stefany stephanie susana suzana tania thalita tuane valquiria veronica
wanda yara zilda zuleica adriane alexandra aline amabile ana anne annie antonieta ariane
ariana arlene beatris berenice camile camilla carina cassia catia celeste cibele clarissa
claudete cleonice creusa daniele danielle darlene debora deise denize dinora edilene
edite edneia elen ellen eliana eliete elisangela elizangela emily emilly erica estefani
eunice fabiola francine franciele franciely gabriely geni gerusa gisela glaucia graciela
greice hellen heloise hosana inês ines irani isis ivana izabel izabela jamile janete
jaqueline jenifer jennifer joelma josefina josilene jucilene julcimara juliane jurema
kaline karine kellen kethellen ketlin laiane laisa lauane leandra leidiane leticia lilia
lisandra lucelia lucinda luna magali maiara mara marcelle mariah marieta marilene marisa
marise marlucia maryana michela mikaela milene mirella mirna monique nadja natacha
nathaly nayara nazare nelma nilda nubia odilia olivia paola patricia rayane rayssa
regiane rejane risoleta rosalina rosane roseane rosimar rosineide sabina samira sheila
shirley silvana silvania sirlei sonia stefani suely sulamita taciana tainara tamara
tatiane tauane terezinha thamires thayna valdirene valentina vanda vanusa vitoria
viviane waleska wilma yolanda zeni zilma zoraide
""".split())

SOBRENOMES = set("""
silva santos oliveira souza sousa rodrigues ferreira alves pereira lima gomes costa ribeiro
martins carvalho almeida lopes soares fernandes vieira barbosa rocha dias nascimento
andrade moreira nunes marques machado mendes freitas cardoso ramos goncalves santana
teixeira araujo cavalcante cavalcanti batista campos moura monteiro correia correa pinto
melo mello cunha reis castro farias faria azevedo bezerra miranda medeiros xavier coelho
barros nogueira pires duarte tavares brito sales lobato moraes morais rezende resende
fonseca peixoto macedo siqueira sampaio aguiar borges bastos guimaraes magalhaes queiroz
queiros leite amaral bispo matos mattos franco vasconcelos vasconcellos jesus cruz paiva
brandao bittencourt camargo cordeiro damasceno diniz esteves fagundes figueiredo fontes
frota galvao garcia godoy godoi goes holanda junqueira lacerda leal leao lemos maia malta
mascarenhas meireles meirelles mesquita novaes novais pacheco padilha paixao pimentel
pinheiro porto prado quintela rabelo rangel rios sa saraiva seixas serra severo simoes
sobral sodre tenorio toledo torres valente veloso viana vilela vidal chaves conceicao assis
assuncao avila barreto barroso bento bueno caldas calado camara carneiro cerqueira couto
dantas domingues feitosa fialho filho neto junior sobrinho freire furtado gusmao guedes
jardim lins loureiro luz mendonca menezes montenegro mota motta muniz nobre ornelas
passos paz pedrosa penha peres perez queiroga rebelo reboucas roque salgado santiago
schmidt silveira spinola valadares varela vaz veiga venancio vilar viveiros wanderley
moreno navarro romero marinho benevides aragao albuquerque arruda bandeira beltrao cabral
campelo coutinho drummond fidalgo flores gama gouveia guerra honorato landim maciel matias
portela abreu acioli aguiar alencar alvarenga alvim amorim antunes aquino arantes azeredo
bacelar baptista barcelos barreira barreto bello bezerra bonfim braga bragança branco
brasil caldeira calheiros calixto camelo campello canuto cardim carmo carreiro carrijo
castelo castilho cavalheiro cezar chagas coimbra conde cordovil cortez cruz dutra
estrela evangelista falcao fausto fernandes ferraz ferro fiuza fonteles fortes fraga
frazao frias garcez gaspar gentil godinho goulart granja gurgel hora jacome jordao
lago lamego lanes leitao lessa liberato linhares lisboa lobo lucena lustosa macario
madeira magno malheiros mano marcondes mariano marins martinez mata mauricio mazza
meira mendes milhomem mourao nader neiva nery noleto norte novaes ourique pacifico
pantoja paranhos parente pastor patricio pedroso peixoto pena pessoa pestana piedade
pimenta pinto pontes prates quaresma queiroga ramalho ramires rego reis ricci rizzo
rocha rodrigues rolim sabino salazar salles sanches santanna santiago sardinha sarmento
seabra serafim sergio severiano silvestre simas sobreira soeiro sotero tabosa taveira
teles telles tolentino trindade uchoa ventura vidigal vilas vilhena viriato zago
""".split())

PARTICULAS = {"da", "de", "do", "das", "dos", "d'", "d’", "del", "della", "di", "du", "van", "von", "y"}

# Palavras que costumam aparecer com inicial maiúscula e NÃO são nomes de pessoa.
PALAVRAS_COMUNS = set("""
excelentissimo excelentissima excelencia exmo exma ilustrissimo ilustrissima ilmo ilma
senhor senhora senhores senhoras sr sra srta srs dr dra drs doutor doutora doutores
prof profa professor professora mestre meritissimo meritissima mm digno digna prezado
prezada prezados caro cara caros
juiz juiza juizo direito vara varas civel civeis criminal criminais tribunal tribunais
justica estado estados federal federais distrito ministerio publico publica poder
judiciario judiciaria legislativo executivo acao acoes processo processos autos autor
autora autores reu re reus requerente requerentes requerido requerida requeridos
reclamante reclamado reclamada impetrante impetrado paciente apelante apelado apelada
agravante agravado agravada embargante embargado recorrente recorrido exequente executado
executada inventariante interessado interessada testemunha testemunhas declarante
depoente outorgante outorgado contratante contratada contratado locador locatario
fiador comarca forum foro termo ata atas audiencia audiencias sentenca decisao despacho
acordao acordaos certidao certidoes certifico certificamos dou fe peticao inicial
contestacao replica recurso apelacao agravo embargos mandado seguranca habeas corpus
data datas brasil brasileira brasileiro brasileiros republica federativa lei leis
decreto portaria resolucao instrucao normativa medida provisoria codigo civil penal
processual trabalho trabalhista artigo artigos art arts inciso incisos paragrafo
paragrafos alinea constituicao emenda sumula sumulas tema uniao municipio municipios
prefeitura prefeito secretaria secretario secretaria governo governador caixa banco
economica nacional instituto seguro social previdencia inss exercito marinha aeronautica
forca forcas armadas aerea comando comandante militar militares policia delegacia
delegado delegada defensoria defensor defensora procuradoria procurador procuradora
advocacia advogado advogada advogados geral ordem superior supremo regional regionais
eleitoral turma turmas camara camaras secao secoes gabinete desembargador desembargadora
ministro ministra relator relatora revisor promotor promotora escrivao escriva oficial
oficiala cartorio registro registros tabeliao tabeliona tabelionato notas imoveis pessoas
naturais juridicas cnpj cpf rg cep oab inss sus ctps cnh pis
janeiro fevereiro abril maio junho julho agosto setembro outubro novembro dezembro
segunda terca quarta quinta sexta sabado domingo feira
rua avenida av travessa alameda rodovia estrada praca largo beco bairro centro cidade
quadra lote setor conjunto bloco apartamento apto casa sala edificio condominio residencial
norte sul leste oeste central
contrato contratos clausula clausulas unico unica primeiro primeira segundo segunda
terceiro terceira quarto quarta quinto quinta sexto setimo oitavo nono decimo
total valor valores local assinatura nome nomes endereco telefone email objeto partes
parte considerando diante ante isso assim portanto pelo pela pelos pelas para com sem
por sobre entre este esta esse essa aquele aquela nos nas aos que qual como quando onde
nao sim sua seu suas seus meu minha nosso nossa vosso vossa ele ela eles elas
no na ao a o os as um uma uns umas em e ou mas se ja tambem ainda apenas
exposto fatos fundamentos pedidos pedido requer requerimento termos nestes neste nesta
atenciosamente cordialmente respeitosamente pede deferimento
anexo anexos documento documentos pagina paginas folha folhas fls fl item itens
santa santo sao nosso nossa senhora deus   igreja
hospital escola colegio universidade faculdade fundacao associacao sindicato empresa
companhia cia ltda me eireli  s.a. grupo servicos comercio industria
rio janeiro  minas gerais mato grosso goias para amapa acre parana bahia sergipe
alagoas pernambuco paraiba ceara piaui maranhao tocantins rondonia roraima amazonas
espirito  brasilia taguatinga ceilandia samambaia  sobradinho planaltina
guara cruzeiro  aguas claras goiania manaus belem recife salvador fortaleza curitiba
florianopolis palmas cuiaba natal teresina maceio aracaju macapa  boa vista velho
 horizonte belo alegre  grande campo campinas  guarulhos osasco niteroi
betim contagem uberlandia londrina joinville
unidade setor secao departamento divisao coordenacao diretoria diretor diretora
presidente presidencia vice gerente gerencia chefe chefia coordenador coordenadora
assessor assessora assessoria analista tecnico tecnica servidor servidora cargo funcao
comissao conselho comite colegiado plenario sessao reuniao pauta ordem dia aberta
encerrada lavrada lida aprovada
objeto conclusao introducao resumo relatorio voto ementa dispositivo fundamentacao
nota tecnica parecer oficio memorando despacho informacao
avos paternos maternos filiacao genitores assunto anexos remetente destinatario
representante representantes legal responsavel recursos humanos pessoal administrativo administrativa financeiro financeira juridico juridica
 dona
""".split())

# Palavras que, imediatamente antes de um nome, indicam homenagem ou lugar
# ("Rua João Pessoa", "Escola Maria Quitéria", "Lei Maria da Penha").
PALAVRAS_LUGAR = set("""
rua avenida av travessa alameda rodovia estrada praca largo viela beco viaduto ponte
escola colegio hospital universidade faculdade fundacao instituto edificio condominio
residencial parque estadio ginasio aeroporto teatro museu biblioteca igreja paroquia
capela lei operacao programa premio projeto cidade municipio bairro vila jardim setor
centro avenidas creche unidade complexo shopping mercado ginasio arena sala auditorio
""".split())

# Expressões que parecem nomes de pessoa mas são lugares ou institutos.
EXPRESSOES_NAO_PESSOA = {
    "joao pessoa", "porto alegre", "belo horizonte", "campo grande", "porto velho",
    "rio branco", "boa vista", "sao paulo", "sao luis", "santa catarina",
    "espirito santo", "rio de janeiro", "mato grosso", "minas gerais", "distrito federal",
    "maria da penha", "nossa senhora", "aguas claras", "vicente pires", "riacho fundo",
}

# Expressões que nunca são substituídas, mesmo contendo um nome detectado
# (o usuário pode acrescentar outras na lista "nunca anonimizar").
EXPRESSOES_PROTEGIDAS = [
    "Lei Maria da Penha", "Lei Carolina Dieckmann", "Lei Pelé", "Lei Aldir Blanc", "Lei Paulo Gustavo",
    "Lei Henry Borel", "Lei Mariana Ferrer", "Lei Lucas", "Lei Joanna Maranhão", "Lei Áurea",
    "Nossa Senhora", "Santa Maria", "São José", "São João", "São Pedro", "São Paulo", "São Luís",
    "Santo Antônio", "Santa Catarina", "Espírito Santo", "Santa Luzia", "Santa Rita",
    "Rio de Janeiro", "Belo Horizonte", "Porto Alegre", "Campo Grande", "Distrito Federal",
]

# Tratamentos que, antes de um nome, autorizam aceitar até um nome isolado.
TRATAMENTOS = {
    "sr", "sra", "srta", "dr", "dra", "senhor", "senhora", "doutor", "doutora",
    "prezado", "prezada", "caro", "cara", "prof", "profa", "professor", "professora",
    "dona", "seu",
}


def _normalizar_conjunto(conjunto: set[str]) -> set[str]:
    from ..texto import normalizar
    return {normalizar(p) for p in conjunto}


PRENOMES = _normalizar_conjunto(PRENOMES)
SOBRENOMES = _normalizar_conjunto(SOBRENOMES)
PALAVRAS_COMUNS = _normalizar_conjunto(PALAVRAS_COMUNS)
