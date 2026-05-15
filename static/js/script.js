// ==========================================================
// I. VARIÁVEIS E FUNÇÕES GLOBAIS (Acessíveis pelo HTML: onclick, onsubmit)
// ==========================================================

// Variáveis de controle para debounce e estado (Globais)
let cnpjTimeout;
let cepTimeout;

// URLs de Rota Flask (Definidas no Jinja - Devem estar no seu TEMPLATE HTML, não aqui!)
// **ATENÇÃO:** As variáveis Jinja ({{ ... }}) abaixo só funcionam se este script estiver no TEMPLATE HTML.
// Se este for um arquivo .js estático, você PRECISA passar essas URLs via data-attributes ou variáveis globais
// definidas no seu template HTML. Assumindo que você as manteve, vamos mantê-las aqui por enquanto.
const URL_EDICAO_BASE = "{{ url_for('editar_contrato', cnpj='CNPJ_PLACEHOLDER') }}";
const URL_EXCLUSAO_BASE = "{{ url_for('excluir_contrato', contrato_id=0) }}";


// --- Funções de Feedback de Erro ---
function showError(fieldId, message) {
    const errorSpan = document.getElementById(fieldId + '-error');
    if (errorSpan) {
        errorSpan.textContent = message;
    }
}

function clearError(fieldId) {
    const errorSpan = document.getElementById(fieldId + '-error');
    if (errorSpan) {
        errorSpan.textContent = '';
    }
}

function setLoading(fieldId, isLoading) {
    const loadingSpan = document.getElementById(fieldId + '-loading');
    if (loadingSpan) {
        loadingSpan.classList.toggle('hidden', !isLoading);
    }
}

// --- Funções Auxiliares de Máscara e Formatação (Globalmente acessíveis) ---

function getValorContratoLimpo() {
    const inputValor = document.getElementById('valor_contrato');
    if (!inputValor) return 0; 
    let valor = inputValor.value.replace(/\./g, '').replace(',', '.'); 
    const valorNumerico = parseFloat(valor);
    return isNaN(valorNumerico) ? 0 : valorNumerico;
}

function aplicarMascaraMonetaria(input) {
    let valor = input.value.replace(/\D/g, '');
    if (valor.length === 0) {
        input.value = '';
        return;
    }
    
    let numCentavos = parseInt(valor, 10);
    valor = String(numCentavos); 

    while (valor.length < 3) {
        valor = '0' + valor;
    }

    let v = valor.replace(/(\d{2})$/, ',$1');
    let partes = v.split(',');
    let parteInteira = partes[0];
    let parteDecimal = partes[1];
    
    parteInteira = parteInteira.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
    
    input.value = parteInteira + ',' + parteDecimal;
}

function formatToBRDate(dateString) {
    if (!dateString) return '';
    const parts = dateString.split('-');
    if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }
    return dateString;
}

function formatToBRL(value) {
    if (typeof value === 'string') {
          value = value.replace(/\D/g, '');
    }
    const num = parseFloat(value / 100);
    if (isNaN(num)) return 'R$ 0,00';
    
    return num.toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: 2
    });
}

function toggleAccessibility() {
    document.body.classList.toggle('high-contrast');
    if (document.body.classList.contains('high-contrast')) {
        localStorage.setItem('highContrastMode', 'enabled');
    } else {
        localStorage.removeItem('highContrastMode');
    }
}

// --- FUNÇÕES DE AÇÃO CRÍTICA (Botões da Tabela/PDF) ---

// Funções de Modal de Exclusão (Corrigidas para estar no escopo global)
function showDeleteModal(contratoId) {
    const deleteForm = document.getElementById('delete-form');
    const deleteModal = document.getElementById('delete-modal');

    if (deleteForm && deleteModal) {
        deleteForm.action = `/delete-contract/${contratoId}`;
        deleteModal.classList.remove('hidden');
    }
}

function closeDeleteModal() {
    const deleteModal = document.getElementById('delete-modal');
    if (deleteModal) {
        deleteModal.classList.add('hidden');
    }
}

// Função de Geração de PDF (Globalmente acessível)
window.generatePDF = function() {
    const filename = renderContractPreview(); 
    const element = document.getElementById('contrato-preview');

    const previewSection = document.getElementById('preview-section');
    const previewHeader = previewSection ? previewSection.querySelector('.bg-gray-100') : null; 
    
    if(previewHeader) {
        previewHeader.style.display = 'none'; 
        element.style.paddingTop = '20px'; 
    }

    const opt = {
        margin: [20, 15, 20, 15], 
        filename: `${filename}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { 
            scale: 3, 
            useCORS: true 
        },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    html2pdf().set(opt).from(element).save().then(() => {
        if(previewHeader) {
            previewHeader.style.display = 'flex';
            element.style.paddingTop = '32px'; 
        }
    });
}; 

// Função de Validação (Globalmente acessível)
function validarFormulario(event) {
    console.log("Validação iniciada."); 

    const cnpjInput = document.getElementById('cnpj');
    const cepInput = document.getElementById('cep');
    const telefoneInput = document.getElementById('telefone');
    const emailInput = document.getElementById('email');
    const valorContratoInput = document.getElementById('valor_contrato');
    const nomeInput = document.getElementById('nome');
    const enderecoInput = document.getElementById('endereco');

    let isValid = true;
    
    clearError('cnpj'); clearError('cep'); clearError('telefone'); 
    clearError('email'); clearError('valor_contrato'); clearError('nome'); 
    clearError('endereco');
    
    // Validações (simplificadas para o resumo, mas o código original está ok)
    // ... (Seu código de validação continua aqui) ...

    const cnpjLimpo = cnpjInput.value ? cnpjInput.value.replace(/\D/g, '') : '';
    if (cnpjLimpo.length !== 14 || nomeInput.value.trim() === '') {
        showError('cnpj', 'CNPJ deve ter 14 dígitos e o nome da empresa deve ser preenchido.');
        isValid = false;
    }

    const cepLimpo = cepInput.value ? cepInput.value.replace(/\D/g, '') : '';
    if (cepLimpo.length !== 8 || enderecoInput.value.trim() === '') {
        showError('cep', 'CEP deve ter 8 dígitos e o endereço deve ser preenchido.');
        isValid = false;
    }

    const telefoneLimpo = telefoneInput.value ? telefoneInput.value.replace(/\D/g, '') : '';
    if (telefoneLimpo.length < 10 || telefoneLimpo.length > 11) {
        showError('telefone', 'Telefone inválido (mín. 10 / máx. 11 dígitos).');
        isValid = false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailInput.value.trim())) {
        showError('email', 'Por favor, insira um endereço de e-mail válido.');
        isValid = false;
    }

    const valorNumerico = getValorContratoLimpo();
    if (valorNumerico <= 0) {
        showError('valor_contrato', 'O valor do contrato deve ser maior que zero.');
        isValid = false;
    }
    
    if (!isValid) {
        console.error("Validação falhou. Impedindo envio."); 
        event.preventDefault(); 
        return false;
    }
    
    console.log("Validação OK. Permitindo envio.");
    return true; 
}


// Função loadContractForEdit (Placeholder Global - Redefinida no DOMContentLoaded)
window.loadContractForEdit = function(el, isPdfPreview = false) {
    console.error("loadContractForEdit chamada antes da inicialização completa do DOM.");
};


// ==========================================================
// II. INICIALIZAÇÃO DO DOM (Onde Event Listeners e Lógica Interna são configurados)
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {
    // Carrega o modo de alto contraste se estiver salvo
    if (localStorage.getItem('highContrastMode') === 'enabled') {
        document.body.classList.add('high-contrast');
    }

    // 1. Variáveis do DOM (const/let locais)
    const form = document.getElementById('contrato-form');
    const formTitle = document.getElementById('form-title');
    const submitBtn = document.getElementById('submit-btn');
    const clearFormBtn = document.getElementById('clear-form-btn');
    const previewPdfBtn = document.getElementById('preview-pdf-btn');

    const idEditInput = document.getElementById('contrato_id_edit');
    const cnpjInput = document.getElementById('cnpj');
    const cepInput = document.getElementById('cep');
    const emailInput = document.getElementById('email');
    const nomeInput = document.getElementById('nome');
    const enderecoInput = document.getElementById('endereco');
    const estadoInput = document.getElementById('estado');
    const valorContratoInput = document.getElementById('valor_contrato');
    const inicioContratoInput = document.getElementById('inicio_contrato');
    const terminoContratoInput = document.getElementById('termino_contrato');
    const abrangenciaContratoInput = document.getElementById('abrangencia_contrato');
    const tipoIndiceSelect = document.getElementById('tipo_indice'); 
    const telefoneInput = document.getElementById('telefone');
    
    // --- Funções Auxiliares de Máscara (Locais) ---
    function maskCNPJ(value) {
        value = value.replace(/\D/g, "");
        value = value.replace(/^(\d{2})(\d)/, "$1.$2");
        value = value.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
        value = value.replace(/\.(\d{3})(\d)/, ".$1/$2");
        value = value.replace(/(\d{4})(\d)/, "$1-$2");
        return value;
    }

    function maskCEP(value) {
        value = value.replace(/\D/g, "");
        value = value.replace(/^(\d{5})(\d)/, "$1-$2");
        return value;
    }

    // 2. FUNÇÕES DE FETCH (Locais)
    // ... (Código fetchBrasilAPI e fetchViaCEP está correto) ...
    
    const fetchBrasilAPI = async function(cnpj) {
        const cleanCnpj = cnpj.replace(/\D/g, '');
        if (cleanCnpj.length !== 14) {
            clearError('cnpj');
            return;
        }
        setLoading('cnpj', true);
        
        try {
            const response = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cleanCnpj}`);
            const data = await response.json();

            if (response.ok) {
                nomeInput.value = data.razao_social || data.nome_fantasia || '';
                enderecoInput.value = `${data.logradouro || ''}, ${data.numero || 'S/N'} - ${data.bairro || ''}, ${data.municipio || ''}`;
                estadoInput.value = data.uf || '';
                cepInput.value = maskCEP(data.cep || ''); 
                clearError('cnpj');
            } else {
                showError('cnpj', data.message || 'CNPJ não encontrado ou inválido.');
                nomeInput.value = '';
            }
        } catch (error) {
            showError('cnpj', 'Erro ao conectar com BrasilAPI.');
        } finally {
            setLoading('cnpj', false);
        }
    }
    
    const fetchViaCEP = async function(cep) {
        const cleanCep = cep.replace(/\D/g, '');
        if (cleanCep.length !== 8) {
            clearError('cep');
            return;
        }
        setLoading('cep', true);
        
        try {
            const response = await fetch(`https://viacep.com.br/ws/${cleanCep}/json/`);
            const data = await response.json();

            if (!data.erro) {
                enderecoInput.value = `${data.logradouro || ''}, ${data.bairro || ''}, ${data.localidade || ''}`;
                estadoInput.value = data.uf || estadoInput.value;
                clearError('cep');
            } else {
                showError('cep', 'CEP não encontrado.');
            }
        } catch (error) {
            showError('cep', 'Erro ao conectar com ViaCEP.');
        } finally {
            setLoading('cep', false);
        }
    }


    // 3. FUNÇÕES DE LIMPEZA, EDIÇÃO E PRÉVIA (Locais)
    
    const handleContratoAction = function(contratoIdentifier) {
        if (contratoIdentifier) {
            const urlFinal = URL_EDICAO_BASE.replace('CNPJ_PLACEHOLDER', contratoIdentifier);
            form.action = urlFinal; 
        }
    }

    const clearForm = function() {
        form.reset();
        idEditInput.value = '';
        formTitle.textContent = 'Cadastrar Novo Contrato';
        submitBtn.textContent = 'Salvar Contrato';
        submitBtn.classList.add('btn-primary');
        submitBtn.classList.remove('bg-yellow-600', 'hover:bg-yellow-700');
        clearFormBtn.style.display = 'none';
        previewPdfBtn.classList.add('hidden');
        form.action = "{{ url_for('index') }}";
        
        clearError('cnpj'); clearError('cep'); clearError('email'); 
        clearError('telefone'); clearError('valor_contrato'); 
        clearError('nome'); clearError('endereco');
    }

    // CRÍTICA: FUNÇÃO DE GERAÇÃO DO HTML DA PRÉVIA (Local)
    const renderContractPreview = function() {
        const contrato = {
            id: idEditInput.value || 'NOVO',
            cnpj: cnpjInput.value,
            nome: nomeInput.value,
            valor: valorContratoInput.value,
            inicio: formatToBRDate(inicioContratoInput.value),
            termino: terminoContratoInput.value ? formatToBRDate(terminoContratoInput.value) : 'Prazo Indeterminado',
            abrangencia: abrangenciaContratoInput.value,
            indice: tipoIndiceSelect.options[tipoIndiceSelect.selectedIndex].text,
            estado: estadoInput.value.toUpperCase(),
            cep: cepInput.value,
            endereco: enderecoInput.value,
            telefone: telefoneInput.value,
            email: emailInput.value,
            valorRaw: valorContratoInput.value.replace(/\D/g, '').replace(',', '') 
        };
        
        const title = `CONTRATO DE PRESTAÇÃO DE SERVIÇOS Nº ${contrato.id}`;

        const contratoHtml = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding-bottom: 10px; border-bottom: 1px solid #ddd;">
                <h1 style="font-size: 22px; font-weight: bold; margin: 0; color: #333;">${title}</h1>
                <img src="https://placehold.co/150x40/3498db/ffffff?text=SUA+LOGO" alt="Logo da Empresa" style="width: 150px; height: 40px;">
            </div>
            
            <h2 style="font-size: 16px; font-weight: bold; margin-bottom: 15px; border-bottom: 2px solid #000; padding-bottom: 5px; text-transform: uppercase;">I. Das Partes Contratantes</h2>
            
            <div class="contrato-dados" style="font-size: 13px; line-height: 1.8; margin-bottom: 25px;">
                <p style="margin-bottom: 15px;">
                    <strong>CONTRATADA:</strong> M.A. Automação, com sede em [CIDADE SEDE], [ENDEREÇO DA SEDE], devidamente inscrita no CNPJ sob o nº [CNPJ DA M.A.], neste ato representada por seus administradores legais.
                </p>
                <p>
                    <strong>CONTRATANTE:</strong> ${contrato.nome}, pessoa jurídica de direito privado, inscrita no CNPJ sob o nº ${contrato.cnpj}, com sede em ${contrato.endereco} - CEP ${contrato.cep}, Estado de ${contrato.estado}. Contato: ${contrato.telefone} / ${contrato.email}.
                </p>
            </div>
            
            <h2 style="font-size: 16px; font-weight: bold; margin-bottom: 15px; border-bottom: 2px solid #000; padding-bottom: 5px; text-transform: uppercase;">II. Objeto e Valor</h2>
            
            <p style="font-size: 13px; line-height: 1.8; margin-bottom: 15px;">
                <strong>CLÁUSULA PRIMEIRA (Objeto):</strong> O presente contrato tem por objeto a prestação de serviços de ${contrato.abrangencia}, conforme as especificações detalhadas no Anexo I.
            </p>
            
            <p style="font-size: 13px; line-height: 1.8; margin-bottom: 25px;">
                <strong>CLÁUSULA SEGUNDA (Valor e Reajuste):</strong> O valor total do contrato é de <strong>${formatToBRL(contrato.valorRaw)}</strong> (${contrato.valor}), a ser pago mensalmente/integralmente. O reajuste anual será baseado no índice ${contrato.indice}.
            </p>

            <h2 style="font-size: 16px; font-weight: bold; margin-bottom: 15px; border-bottom: 2px solid #000; padding-bottom: 5px; text-transform: uppercase;">III. Prazo e Vigência</h2>
            
            <p style="font-size: 13px; line-height: 1.8; margin-bottom: 50px;">
                <strong>CLÁUSULA TERCEIRA:</strong> O presente contrato terá vigência a partir de <strong>${contrato.inicio}</strong>. O prazo de término é: ${contrato.termino}.
            </p>
            
            <div style="display: flex; justify-content: space-around; margin-top: 50px; padding-top: 10px; font-size: 14px;">
                <div style="text-align: center; border-top: 1px solid #000; padding-top: 10px; width: 40%;">
                    CONTRATANTE: ${contrato.nome}
                </div>
                <div style="text-align: center; border-top: 1px solid #000; padding-top: 10px; width: 40%;">
                    CONTRATADA: M.A. Automação
                </div>
            </div>
        `;

        document.getElementById('contrato-preview').innerHTML = contratoHtml;
        return `Contrato_${contrato.nome.substring(0, 15).replace(/[^a-zA-Z0-9]/g, '_')}_${contrato.id}`;
    }

    // 4. ATRIBUIÇÃO DOS EVENT LISTENERS
    
    cnpjInput.addEventListener('input', (e) => {
        e.target.value = maskCNPJ(e.target.value);
        clearTimeout(cnpjTimeout);
        if (e.target.value.replace(/\D/g, '').length === 14) {
            cnpjTimeout = setTimeout(() => fetchBrasilAPI(e.target.value), 1000);
        } else {
            clearError('cnpj');
        }
    });
    
    cepInput.addEventListener('input', (e) => {
        e.target.value = maskCEP(e.target.value);
        clearTimeout(cepTimeout);
        if (e.target.value.replace(/\D/g, '').length === 8) {
            cepTimeout = setTimeout(() => fetchViaCEP(e.target.value), 1000);
        } else {
            clearError('cep');
        }
    });

    // Listener do botão de Limpar
    clearFormBtn.addEventListener('click', clearForm);
    
    // 5. REDEFINIÇÃO DAS FUNÇÕES GLOBAIS (window.x) PARA USAR AS VARS LOCAIS
    
    // Redefine a função loadContractForEdit (Chamada pelo 'onclick' da tabela)
    window.loadContractForEdit = function(el, isPdfPreview = false) {
        const data = el.dataset;

        idEditInput.value = data.id;
        cnpjInput.value = maskCNPJ(data.cnpj);
        nomeInput.value = data.nome;
        // O valor é formatado de BRL para texto no input
        valorContratoInput.value = formatToBRL(data.valorRaw).replace('R$', '').trim(); 
        inicioContratoInput.value = data.inicio;
        terminoContratoInput.value = data.termino;
        abrangenciaContratoInput.value = data.abrangencia;
        tipoIndiceSelect.value = data.indice;
        estadoInput.value = data.estado;
        cepInput.value = maskCEP(data.cep);
        enderecoInput.value = data.endereco;
        telefoneInput.value = data.telefone;
        emailInput.value = data.email;
        
        if (!isPdfPreview) {
            formTitle.textContent = `Editar Contrato ID: ${data.id}`;
            submitBtn.textContent = 'Atualizar Contrato';
            submitBtn.classList.remove('btn-primary');
            submitBtn.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
            clearFormBtn.style.display = 'inline-block';
            previewPdfBtn.classList.remove('hidden');

            window.scrollTo({ top: 0, behavior: 'smooth' });
            
            handleContratoAction(data.cnpj); 
        } else {
            showContractPreview();
        }
    };
    
    window.showContractPreview = function() {
        renderContractPreview(); 
        document.getElementById('preview-section').classList.remove('hidden');
    }

    window.hideContractPreview = function() {
        document.getElementById('preview-section').classList.add('hidden');
    }

}); // Fim do DOMContentLoaded