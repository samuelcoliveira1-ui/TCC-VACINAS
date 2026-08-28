# API 1º Semestre ADS - Vacina Brasil Bot (NexusDev)

> Status do Projeto: Sprint 3 - Concluída ✅ (11/05 - 31/05)

## 🎬 Demonstração

[![Vacina Brasil Bot - Demonstração](https://img.youtube.com/vi/wad36pTf6_Y/maxresdefault.jpg)](https://youtu.be/wad36pTf6_Y)

> 🔗 [Clique para assistir no YouTube](https://youtu.be/wad36pTf6_Y)

---

## 🏅 Desafio <a id="desafio"></a>

Desenvolver um assistente virtual para Telegram focado em saúde pública. O bot informa ao usuário **as vacinas recomendadas de acordo com a faixa etária selecionada** e mostra a **cobetura vacinal de todas as regiões do Brasil**, utilizando **scraping** e **dados processados localmente a partir de arquivos JSON**.

---

## 📋 Product Backlog <a id="backlog"></a>

| Rank | Prioridade | User Story | Sprint |
| :--- | :---: | :--- | :---: |
| 1 | Baixa | Como usuário, quero visualizar um botão com mais informações sobre o assistente e sua equipe de desenvolvimento para entender a origem da ferramenta. | 3 |
| 2 | Baixa | Como usuário, quero um botão para visualizar e baixar os calendários vacinais originais (PDFs) para guardar ou imprimir. | 3 |
| 3 | Média | Como usuário, quero um menu mais limpo e organizado, com submenus, para não ficar confuso com muitas opções na mesma tela. | 3 |
| 4 | Média | Garantir que os nomes das vacinas estejam idênticos em todas as bases de dados e no código para evitar bugs nas consultas. | 3 |
| 5 | Alta | Como usuário, quero poder digitar perguntas de forma livre (ex: "quais vacinas pra idoso?") e ser compreendido pelo bot, sem precisar clicar em botões. | 3 |
| 6 | Alta | Como usuário, quero poder pesquisar a cobertura vacinal especificamente da minha cidade ou macrorregião, e não apenas do estado todo. | 3 |
| 7 | Alta | Como usuário, quero informar meu endereço ou enviar minha localização para que o bot mostre o posto de saúde mais próximo. | 3 |

---

## ✅ Definition of Ready (DoR)

| Critério | Descrição |
| :--- | :--- |
| **Descrição Clara** | A User Story está bem escrita e compreensível para toda a equipe. |
| **Critérios de Aceitação** | As regras de validação para a tarefa estão descritas. |
| **Estimativa Realizada** | A tarefa possui pontuação de esforço (Story Points) definida. |
| **Responsável Atribuído** | Há um membro da NexusDev designado para a execução no Jira. |
| **Dependências Resolvidas** | Bloqueios externos ou técnicos foram tratados antes do início. |

---

## ✅ Definition of Done (DoD)

| Critério | Descrição |
| :--- | :--- |
| **Funcionalidades Implementadas** | Botões `Saiba Mais ℹ️`, `Ver ou Baixar PDF`, integração com Ollama e interpretação de linguagem natural, localização de unidades de saúde próximas com base em endereços. |
| **Revisão de Código** | O código foi revisado por outro membro ou validado tecnicamente. |
| **Zero APIs Externas** | A entrega utiliza apenas scraping e processamento local de dados, conforme o requisito. |
| **Integração no Git** | O código foi mergeado no branch principal sem conflitos. |
| **Validação do PO** | O Product Owner validou que a entrega atende à necessidade mínima do usuário. |

---

## 🎓 Equipe <a id="equipe"></a>

<div align="center">

| Nome | Função | LinkedIn & GitHub |
| :--------------------- | :-----------: | :-----------------------------------------------------------------------------------------------------------: |
| Nicolas Fonseca Meira | Scrum Master | [<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linkedin/linkedin-original.svg" width="24"/>](https://www.linkedin.com/in/nicolas-fonseca-60386130b/) [![GitHub Badge](https://img.shields.io/badge/GitHub-111217?style=flat-square&logo=github&logoColor=white)](https://github.com/NicolasFonsecaM) |
| Miguel Silva Gomes | Product Owner | [<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linkedin/linkedin-original.svg" width="24"/>](https://www.linkedin.com/in/miguelsg479/) [![GitHub Badge](https://img.shields.io/badge/GitHub-111217?style=flat-square&logo=github&logoColor=white)](https://github.com/miguelsg97) |
| Gabriel Yudi Fujimoto | Scrum Team | [<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linkedin/linkedin-original.svg" width="24"/>](https://www.linkedin.com/in/gabriel-fujimoto-a90239367/) [![GitHub Badge](https://img.shields.io/badge/GitHub-111217?style=flat-square&logo=github&logoColor=white)](https://github.com/fujimotogabriel) |

</div>
