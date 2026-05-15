# Sistema de Gestão de Contratos - M.A. Automação

> **Desenvolvimento de um software com framework web para a empresa M.A. Automação como parte do portfólio acadêmico para a UNIVESP. A solução aplica conceitos avançados de Engenharia de Software, Ciência de Dados e Segurança da Informação.**

<p align="center">
  <img src="dashboard.png" alt="Dashboard M.A. Automação" width="800">
</p>

## 🚀 Sobre o Projeto
O **CadClientBR** (M.A. Automação) foi concebido para suprir a necessidade de organização e padronização na emissão de contratos. O foco principal foi a criação de uma ferramenta robusta que eliminasse erros manuais e garantisse que todos os documentos gerados seguissem as cláusulas jurídicas atualizadas, proporcionando agilidade e segurança estratégica.

## 🛠️ Tecnologias e Ferramentas
* **Linguagem**: Python 3.x
* **Framework Web**: Flask (desenvolvimento ágil e modular)
* **Banco de Dados**: SQLAlchemy (ORM gerenciando SQLite para desenvolvimento e PostgreSQL)
* **Visualização de Dados**: Chart.js (Dashboards interativos com tooltips)
* **Front-end**: HTML5 e CSS3 (Bootstrap) com foco em UX/UI

## 📊 Inteligência de Dados e Dashboards
A aplicação transforma dados brutos em indicadores estratégicos através de:
* **Evolução Temporal**: Gráficos de linha para monitoramento de receita e sazonalidade.
* **Análise de Exposição**: Gráficos de setores para segmentação de índices de reajuste (IPCA, IGPM, INPC).
* **Geolocalização**: Mapeamento de demanda por regiões e bairros de São Paulo.
* **Interatividade**: Uso de *tooltips* para detalhamento de valores específicos ao passar o cursor sobre os gráficos.

## 🛡️ Qualidade e Segurança (Destaque Acadêmico)
Este projeto mantém um alto padrão de governança de código e manutenção proativa:
* **Segurança (Dependabot)**: Monitoramento automático e mitigação de vulnerabilidades em dependências (ex: atualização crítica da biblioteca `Pillow`).
* **Integração Contínua (CI)**: Uso de **GitHub Actions** para validação automática de código e workflows de aplicação Python.
* **Resiliência**: Refatoração constante de bibliotecas críticas para garantir proteção contra falhas de segurança conhecidas.

## ⚙️ Como Instalar e Executar
1. **Clone o repositório**: `git clone https://github.com/seu-usuario/contrat_cond.git`
2. **Crie um ambiente virtual**: `python -m venv venv`
3. **Ative o venv**:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. **Instale as dependências**: `pip install -r requirements.txt`
5. **Inicie o servidor**: `flask run`

---

## 🎯 Conclusão e Aprendizados
O desenvolvimento deste projeto permitiu a aplicação prática de:
1. **Persistência de Dados**: Modelagem eficiente via SQLAlchemy para garantir a integridade das informações.
2. **Data Storytelling**: Visualização de dados focada em facilitar a tomada de decisão gerencial.
3. **Ciclo de Vida de Software**: Implementação de práticas modernas de versionamento, teste e segurança.

---
**Curso**: Engenharia da Computação / Ciência de Dados – UNIVESP  
**Polo**: Parque Bristol
