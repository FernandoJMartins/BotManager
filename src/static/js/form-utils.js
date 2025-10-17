/**
 * Utilitários para formulários - Reutilizável em todo o sistema
 * Funções para validação, notificações, upload de arquivos, loading, planos, etc.
 *
 * Como usar rapidamente:
 * 1) Inclua este arquivo no template (já está nos seus templates):
 *    <script src="{{ url_for('static', filename='js/form-utils.js') }}"></script>
 * 2) Opcional: personalize os IDs padrão com setFormUtilsConfig({...}) por página.
 * 3) Use showError/showSuccess, showLoading/hideLoading, validateBotInGroups, etc.
 */

// ==================== CONFIGURAÇÃO GLOBAL ====================
const FormUtilsDefaultConfig = {
  // containers de notificação
  errorDisplayId: "errorDisplay",
  errorTitleId: "errorTitle",
  errorMessageId: "errorMessage",
  successDisplayId: "successDisplay",
  successTitleId: "successTitle",
  successMessageId: "successMessage",
  // loading overlay
  loadingOverlayId: "loadingOverlay",
  loadingTitleId: "loadingTitle",
  loadingMessageId: "loadingMessage",
  // steps
  stepIds: ["step1", "step2", "step3", "step4"],
  // botões
  submitBtnId: "submitBtn",
  submitTextId: "submitText",
  cancelBtnId: "cancelBtn",
  // textos padrão
  submitLoadingText: "Validando...",
};

let FormUtilsConfig = { ...FormUtilsDefaultConfig };

function setFormUtilsConfig(cfg) {
  FormUtilsConfig = { ...FormUtilsConfig, ...(cfg || {}) };
}

// ==================== NOTIFICAÇÕES ====================

function showError(title, message, idsOverride) {
  const ids = { ...FormUtilsConfig, ...(idsOverride || {}) };
  const errorDisplay = document.getElementById(ids.errorDisplayId);
  const errorTitle = document.getElementById(ids.errorTitleId);
  const errorMessage = document.getElementById(ids.errorMessageId);

  if (errorDisplay && errorTitle && errorMessage) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorDisplay.style.display = "block";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function hideError() {
  const errorDisplay = document.getElementById(FormUtilsConfig.errorDisplayId);
  if (errorDisplay) {
    errorDisplay.style.display = "none";
  }
}

function showSuccess(title, message, idsOverride) {
  const ids = { ...FormUtilsConfig, ...(idsOverride || {}) };
  const successDisplay = document.getElementById(ids.successDisplayId);
  const successTitle = document.getElementById(ids.successTitleId);
  const successMessage = document.getElementById(ids.successMessageId);

  if (successDisplay && successTitle && successMessage) {
    successTitle.textContent = title;
    successMessage.textContent = message;
    successDisplay.style.display = "block";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function hideSuccess() {
  const successDisplay = document.getElementById(
    FormUtilsConfig.successDisplayId
  );
  if (successDisplay) {
    successDisplay.style.display = "none";
  }
}

// ==================== LOADING / STEPS ====================
let isSubmitting = false;

function showLoading(override) {
  const ids = { ...FormUtilsConfig, ...(override || {}) };
  const overlay = document.getElementById(ids.loadingOverlayId);
  const submitBtn = document.getElementById(ids.submitBtnId);
  const cancelBtn = document.getElementById(ids.cancelBtnId);
  const submitText = document.getElementById(ids.submitTextId);
  const spinner = submitBtn?.querySelector(".btn-spinner");

  if (overlay) overlay.style.display = "flex";
  if (submitBtn) submitBtn.disabled = true;
  if (cancelBtn) cancelBtn.style.pointerEvents = "none";
  if (submitText) {
    // guarda o texto original se ainda não guardado
    if (!submitText.getAttribute("data-original-text")) {
      submitText.setAttribute(
        "data-original-text",
        submitText.textContent || ""
      );
    }
    submitText.textContent =
      ids.submitLoadingText || FormUtilsConfig.submitLoadingText;
  }
  if (spinner) spinner.style.display = "inline-block";
  isSubmitting = true;
}

function hideLoading(override) {
  const ids = { ...FormUtilsConfig, ...(override || {}) };
  const overlay = document.getElementById(ids.loadingOverlayId);
  const submitBtn = document.getElementById(ids.submitBtnId);
  const cancelBtn = document.getElementById(ids.cancelBtnId);
  const submitText = document.getElementById(ids.submitTextId);
  const spinner = submitBtn?.querySelector(".btn-spinner");

  if (overlay) overlay.style.display = "none";
  if (submitBtn) submitBtn.disabled = false;
  if (cancelBtn) cancelBtn.style.pointerEvents = "auto";
  if (submitText)
    submitText.textContent =
      submitText.getAttribute("data-original-text") || "Salvar";
  if (spinner) spinner.style.display = "none";
  isSubmitting = false;
}

function updateLoadingStep(stepNumber, status = "active", opts) {
  const ids = { ...FormUtilsConfig };
  const stepId = ids.stepIds[stepNumber - 1] || `step${stepNumber}`;
  const step = document.getElementById(stepId);
  if (step) {
    step.className = `step ${status}`;
    if (status === "completed") {
      step.innerHTML = step.innerHTML.replace("⏳", "✓");
    } else if (status === "error") {
      step.innerHTML = step.innerHTML.replace("⏳", "✗");
    } else if (status === "active") {
      step.innerHTML = step.innerHTML.replace("✓", "⏳").replace("✗", "⏳");
    }
  }

  const messagesDefault = {
    1: "Verificando se o token é válido...",
    2: "Testando acesso ao grupo VIP como admin...",
    3: "Testando acesso ao grupo de notificações como admin...",
    4: "Criando e ativando seu bot...",
  };
  const messages = opts && opts.messages ? opts.messages : messagesDefault;
  const loadingMessageEl = document.getElementById(ids.loadingMessageId);
  if (loadingMessageEl && messages[stepNumber]) {
    loadingMessageEl.textContent = messages[stepNumber];
  }
}

// ==================== FORMATAÇÃO ====================

function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatGroupId(input) {
  let value = input.value.replace(/[^\d-]/g, "");
  if (value && !value.startsWith("-")) {
    value = "-" + value;
  }
  input.value = value;
}

// ==================== UPLOAD DE ARQUIVOS ====================

function handleMediaUpload(input, previewId = "mediaPreview", options = {}) {
  const file = input.files[0];
  const previewContainer = document.getElementById(previewId);
  const fileLabel = input.nextElementSibling;
  const uploadText = fileLabel?.querySelector(".upload-text");
  const uploadLimit = fileLabel?.querySelector(".upload-limit");

  // Configurações padrão
  const config = {
    // Imagens compatíveis com Telegram sendPhoto: prefira JPEG/PNG
    allowedTypes: [
      "image/jpeg",
      "image/jpg",
      "image/png",
      // vídeos suportados para sendVideo
      "video/mp4",
      "video/avi",
      "video/quicktime",
      "video/x-msvideo",
      "video/webm",
      "video/x-matroska",
    ],
    maxVideoSize: 50 * 1024 * 1024, // 50MB (Telegram)
    maxImageSize: 10 * 1024 * 1024, // 10MB (limite do sendPhoto)
    ...options,
  };

  if (!file) return;

  // Validar formato
  if (!config.allowedTypes.includes(file.type.toLowerCase())) {
    const isImage = file.type.startsWith("image/");
    const isVideo = file.type.startsWith("video/");
    const message = isImage
      ? "Formato de imagem não suportado! Use apenas JPG ou PNG."
      : isVideo
      ? "Formato de vídeo não suportado! Use MP4, AVI, MOV, MKV ou WebM."
      : "Formato de arquivo não suportado!";
    alert(message);
    input.value = "";
    return false;
  }

  // Validar tamanho
  const isVideo = file.type.startsWith("video/");
  const isImage = file.type.startsWith("image/");
  // Reforço: limitar imagens apenas a JPG/PNG mesmo que o browser reporte image/* genérico
  if (
    isImage &&
    !["image/jpeg", "image/jpg", "image/png"].includes(file.type.toLowerCase())
  ) {
    alert("Use apenas imagens JPG ou PNG para evitar falhas no Telegram.");
    input.value = "";
    return false;
  }
  const maxSize = isVideo ? config.maxVideoSize : config.maxImageSize;

  if (file.size > maxSize) {
    const maxSizeMB = maxSize / 1024 / 1024;
    const fileSizeMB = file.size / 1024 / 1024;
    alert(
      `Arquivo muito grande! Tamanho: ${fileSizeMB.toFixed(
        1
      )}MB, Máximo: ${maxSizeMB}MB`
    );
    input.value = "";
    return false;
  }

  // Atualizar visual do botão
  if (uploadText) uploadText.textContent = file.name;
  if (uploadLimit) uploadLimit.textContent = `(${formatFileSize(file.size)})`;
  if (fileLabel) fileLabel.classList.add("file-selected");

  // Mostrar preview
  if (previewContainer) {
    previewContainer.style.display = "block";

    let previewHTML = `
      <div class="file-info">
        <div class="file-icon">
          <i class="fas fa-${
            isImage ? "image" : isVideo ? "video" : "file"
          }"></i>
        </div>
        <div class="file-details">
          <span class="file-name">${file.name}</span>
          <span class="file-size">${formatFileSize(file.size)}</span>
          <span class="file-type">${
            isVideo ? "Vídeo" : isImage ? "Imagem" : "Arquivo"
          }</span>
        </div>
        <button type="button" class="remove-file-btn" onclick="clearSelection('${
          input.id
        }', '${previewId}')">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;

    if (isImage) {
      const reader = new FileReader();
      reader.onload = function (e) {
        previewHTML += `<img src="${e.target.result}" alt="Preview" class="media-preview-img">`;
        previewContainer.innerHTML = previewHTML;
      };
      reader.readAsDataURL(file);
    } else if (isVideo) {
      const reader = new FileReader();
      reader.onload = function (e) {
        previewHTML += `
          <video controls class="media-preview-video">
            <source src="${e.target.result}" type="${file.type}">
            Seu navegador não suporta o elemento de vídeo.
          </video>`;
        previewContainer.innerHTML = previewHTML;
      };
      reader.readAsDataURL(file);
    } else {
      previewContainer.innerHTML = previewHTML;
    }
  }

  return true;
}

function handleAudioUpload(input, previewId = "audioPreview") {
  const file = input.files[0];
  const previewContainer = document.getElementById(previewId);
  const fileLabel = input.nextElementSibling;
  const uploadText = fileLabel?.querySelector(".upload-text");
  const uploadLimit = fileLabel?.querySelector(".upload-limit");

  if (!file) return;

  // Validar formato
  const allowedAudioTypes = ["audio/ogg", "audio/opus", "application/ogg"];
  if (
    !allowedAudioTypes.includes(file.type.toLowerCase()) &&
    !file.name.toLowerCase().endsWith(".ogg")
  ) {
    alert("Formato não suportado! Use apenas arquivos OGG.");
    input.value = "";
    return false;
  }

  // Validar tamanho
  const maxSize = 20 * 1024 * 1024; // 20MB
  if (file.size > maxSize) {
    const fileSizeMB = file.size / 1024 / 1024;
    alert(
      `Áudio muito grande! Tamanho: ${fileSizeMB.toFixed(1)}MB, Máximo: 20MB`
    );
    input.value = "";
    return false;
  }

  // Atualizar visual
  if (uploadText) uploadText.textContent = file.name;
  if (uploadLimit) uploadLimit.textContent = `(${formatFileSize(file.size)})`;
  if (fileLabel) fileLabel.classList.add("file-selected");

  // Preview
  if (previewContainer) {
    previewContainer.style.display = "block";
    previewContainer.innerHTML = `
      <div class="file-info">
        <div class="file-icon"><i class="fas fa-music"></i></div>
        <div class="file-details">
          <span class="file-name">${file.name}</span>
          <span class="file-size">${formatFileSize(file.size)}</span>
          <span class="file-type">Áudio OGG</span>
        </div>
        <button type="button" class="remove-file-btn" onclick="clearSelection('${
          input.id
        }', '${previewId}')">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <audio controls class="audio-preview">
        <source src="${URL.createObjectURL(file)}" type="${file.type}">
        Seu navegador não suporta o elemento de áudio.
      </audio>
    `;
  }

  return true;
}

function clearSelection(inputId, previewId) {
  const input = document.getElementById(inputId);
  const previewContainer = document.getElementById(previewId);
  const fileLabel = input?.nextElementSibling;
  const uploadText = fileLabel?.querySelector(".upload-text");
  const uploadLimit = fileLabel?.querySelector(".upload-limit");

  if (input) input.value = "";
  if (previewContainer) {
    previewContainer.style.display = "none";
    previewContainer.innerHTML = "";
  }

  if (uploadText) {
    uploadText.textContent = inputId.includes("audio")
      ? "Escolher Áudio"
      : "Escolher Mídia";
  }
  if (uploadLimit) {
    uploadLimit.textContent = inputId.includes("audio")
      ? "(Máx: 25MB)"
      : "(Máx: 50MB)";
  }
  if (fileLabel) {
    fileLabel.classList.remove("file-selected");
  }
}

// Aliases para manter compatibilidade
function clearMediaSelection() {
  clearSelection("welcome_image", "mediaPreview");
}

function clearAudioSelection() {
  clearSelection("welcome_audio", "audioPreview");
}

// ==================== VALIDAÇÕES ====================
function validateTelegramToken(token) {
  const tokenPattern = /^\d+:[A-Za-z0-9_-]+$/;
  return tokenPattern.test(token);
}

function validateGroupId(groupId) {
  return groupId && groupId.startsWith("-") && !isNaN(groupId.substring(1));
}

async function validateBotInGroups(token, vipGroupId, logsGroupId) {
  try {
    // Validar token e obter info do bot
    const botInfoResponse = await fetch(
      `https://api.telegram.org/bot${token}/getMe`
    );

    if (!botInfoResponse.ok) {
      throw new Error("Token inválido");
    }

    const botInfoData = await botInfoResponse.json();
    if (!botInfoData.ok) {
      throw new Error("Token inválido");
    }

    const botId = botInfoData.result.id;

    // Verificar grupo VIP
    const vipResponse = await fetch(
      `https://api.telegram.org/bot${token}/getChatMember?chat_id=${vipGroupId}&user_id=${botId}`
    );
    const vipData = await vipResponse.json();

    if (!vipData.ok) {
      throw new Error(
        `Erro no grupo VIP: ${vipData.description || "Bot não está no grupo"}`
      );
    }

    if (!["administrator", "creator"].includes(vipData.result.status)) {
      throw new Error(`Bot precisa ser administrador no grupo VIP`);
    }

    // Verificar grupo de logs
    const logsResponse = await fetch(
      `https://api.telegram.org/bot${token}/getChatMember?chat_id=${logsGroupId}&user_id=${botId}`
    );
    const logsData = await logsResponse.json();

    if (!logsData.ok) {
      throw new Error(
        `Erro no grupo de notificações: ${
          logsData.description || "Bot não está no grupo"
        }`
      );
    }

    if (!["administrator", "creator"].includes(logsData.result.status)) {
      throw new Error(`Bot precisa ser administrador no grupo de notificações`);
    }

    return true;
  } catch (error) {
    throw error;
  }
}

// ==================== GERENCIADOR DE PLANOS ====================

function initPlanManager(opts) {
  const container = document.getElementById(
    (opts && opts.containerId) || "plans-list"
  );
  if (!container) return;
  updateRemoveButtons(opts);
}

function addPlan(opts) {
  const containerId = (opts && opts.containerId) || "plans-list";
  const container = document.getElementById(containerId);
  if (!container) return;

  const plans = container.querySelectorAll(".plan-item");
  if (plans.length >= 10) {
    alert("Máximo de 10 planos permitidos");
    return;
  }

  const newPlan = document.createElement("div");
  newPlan.className = "plan-item";
  newPlan.innerHTML = `
      <div class="plan-col-name">
        <input type="text" class="form-input" name="plan_names[]" placeholder="Novo Plano" maxlength="50" />
      </div>
      <div class="plan-col-value">
        <input type="number" class="form-input" name="pix_values[]" placeholder="19.90" step="0.01" min="0.01" />
      </div>
      <div class="plan-col-duration">
        <select class="form-select" name="plan_duration[]">
          <option value="">Selecione...</option>
          <option value="semanal">Semanal</option>
          <option value="quinzenal">Quinzenal</option>
          <option value="mensal" selected>Mensal</option>
          <option value="trimestral">Trimestral</option>
          <option value="semestral">Semestral</option>
          <option value="anual">Anual</option>
          <option value="vitalicio">Vitalício</option>
        </select>
      </div>
      <div class="plan-col-actions">
        <button type="button" class="btn-remove" onclick="removePlan(this, {containerId: '${containerId}'})" title="Remover plano">
          <i class="fas fa-trash"></i>
        </button>
      </div>`;

  container.appendChild(newPlan);
  updateRemoveButtons(opts);
}

function removePlan(button, opts) {
  const container = document.getElementById(
    (opts && opts.containerId) || "plans-list"
  );
  if (!container) return;
  const plans = container.querySelectorAll(".plan-item");
  if (plans.length <= 1) {
    alert("Deve haver pelo menos um plano configurado!");
    return;
  }
  const planItem = button.closest(".plan-item");
  if (planItem) planItem.remove();
  updateRemoveButtons(opts);
}

function updateRemoveButtons(opts) {
  const container = document.getElementById(
    (opts && opts.containerId) || "plans-list"
  );
  if (!container) return;
  const plans = container.querySelectorAll(".plan-item");
  const removeButtons = container.querySelectorAll(".btn-remove");
  removeButtons.forEach((btn) => {
    btn.style.display = plans.length > 1 ? "inline-flex" : "none";
  });
}

// ==================== AUTO-INIT ====================

document.addEventListener("DOMContentLoaded", function () {
  // Auto-formatação de IDs de grupo
  const groupIdInputs = document.querySelectorAll(".group-id-input");
  groupIdInputs.forEach((input) => {
    input.addEventListener("input", function () {
      formatGroupId(this);
    });
  });

  // Fechar notificações ao clicar no X
  const errorCloseBtn = document.querySelector(
    `#${FormUtilsConfig.errorDisplayId} button`
  );
  const successCloseBtn = document.querySelector(
    `#${FormUtilsConfig.successDisplayId} button`
  );

  if (errorCloseBtn) {
    errorCloseBtn.addEventListener("click", hideError);
  }

  if (successCloseBtn) {
    successCloseBtn.addEventListener("click", hideSuccess);
  }
});

// Expondo funções no escopo global para uso inline em templates
window.setFormUtilsConfig = setFormUtilsConfig;
window.showError = showError;
window.hideError = hideError;
window.showSuccess = showSuccess;
window.hideSuccess = hideSuccess;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.updateLoadingStep = updateLoadingStep;
window.formatFileSize = formatFileSize;
window.formatGroupId = formatGroupId;
window.handleMediaUpload = handleMediaUpload;
window.handleAudioUpload = handleAudioUpload;
window.clearSelection = clearSelection;
window.clearMediaSelection = clearMediaSelection;
window.clearAudioSelection = clearAudioSelection;
window.validateTelegramToken = validateTelegramToken;
window.validateGroupId = validateGroupId;
window.validateBotInGroups = validateBotInGroups;
window.initPlanManager = initPlanManager;
window.addPlan = addPlan;
window.removePlan = removePlan;
window.updateRemoveButtons = updateRemoveButtons;

// ==================== VALIDADORES EXTRAS (export) ====================
function validatePlanSection(sel) {
  const pixInputs = document.querySelectorAll(sel.pixSelector);
  const planInputs = document.querySelectorAll(sel.nameSelector);
  const durationInputs = document.querySelectorAll(sel.durationSelector);

  const hasValue = Array.from(pixInputs).some(
    (input) => input.value && parseFloat(input.value) >= 0.01
  );
  const hasName = Array.from(planInputs).some(
    (input) => input.value && input.value.trim()
  );
  const hasDuration = Array.from(durationInputs).some(
    (input) => input.value && input.value.trim()
  );

  if (!hasValue)
    return {
      ok: false,
      title: "Erro de Validação",
      message: "Configure pelo menos um valor PIX para o seu bot!",
    };
  if (!hasName)
    return {
      ok: false,
      title: "Erro de Validação",
      message: "Configure pelo menos um nome de plano para o seu bot!",
    };
  if (!hasDuration)
    return {
      ok: false,
      title: "Erro de Validação",
      message: "Configure pelo menos uma duração de plano para o seu bot!",
    };
  return { ok: true };
}
window.validatePlanSection = validatePlanSection;

function validateOrderBumpSection(cfg) {
  const form = cfg.form || document.querySelector("form");
  const nameEl = form?.querySelector(`[name="${cfg.nameId || "name"}"]`);
  const priceEl = form?.querySelector(`[name="${cfg.priceId || "price"}"]`);
  const messageEl = form?.querySelector(
    `[name="${cfg.messageName || "message"}"]`
  );
  const deliverableEl = form?.querySelector(
    `[name="${cfg.deliverableName || "deliverable_message"}"]`
  );
  const acceptEl = form?.querySelector(
    `[name="${cfg.acceptTextName || "accept_button_text"}"]`
  );
  const declineEl = form?.querySelector(
    `[name="${cfg.declineTextName || "decline_button_text"}"]`
  );

  if (!nameEl || !nameEl.value.trim())
    return {
      ok: false,
      title: "Nome obrigatório",
      message: "Informe o nome da oferta.",
    };
  if (
    !priceEl ||
    isNaN(parseFloat(priceEl.value)) ||
    parseFloat(priceEl.value) < 0.01
  )
    return {
      ok: false,
      title: "Preço inválido",
      message: "Informe um preço válido (mínimo R$ 0,01).",
    };
  if (!messageEl || !messageEl.value.trim())
    return {
      ok: false,
      title: "Mensagem obrigatória",
      message: "Informe a mensagem da oferta.",
    };
  if (!deliverableEl || !deliverableEl.value.trim())
    return {
      ok: false,
      title: "Entregável obrigatório",
      message:
        "Informe a mensagem do entregável que será enviada após o pagamento.",
    };
  if (!acceptEl || !acceptEl.value.trim())
    return {
      ok: false,
      title: "Texto do botão",
      message: "Informe o texto do botão de aceitar.",
    };
  if (!declineEl || !declineEl.value.trim())
    return {
      ok: false,
      title: "Texto do botão",
      message: "Informe o texto do botão de recusar.",
    };
  return { ok: true };
}
window.validateOrderBumpSection = validateOrderBumpSection;

// ==================== SUBMIT HELPER (DRY) ====================
/**
 * Registra um submit handler padrão com loading + sucesso/erro.
 * Útil para telas simples (ex.: editar bot) onde basta enviar o formulário.
 *
 * opts: {
 *   formSelector?: string (default 'form.bot-form')
 *   validatePlans?: boolean (default true)
 *   successTitle?: string
 *   successMessage?: string
 *   redirectUrl?: string
 *   submitLoadingText?: string (default 'Salvando...')
 * }
 */
function registerSimpleFormSubmit(opts = {}) {
  const form = document.querySelector(opts.formSelector || "form.bot-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById(FormUtilsConfig.submitBtnId);
    if (submitBtn?.disabled) return;

    // Validação mínima de planos (opcional)
    if (opts.validatePlans !== false) {
      const planCheck = validatePlanSection({
        pixSelector: 'input[name="pix_values[]"]',
        nameSelector: 'input[name="plan_names[]"]',
        durationSelector: 'select[name="plan_duration[]"]',
      });
      if (!planCheck.ok) {
        showError(planCheck.title, planCheck.message);
        return;
      }
    }

    showLoading({ submitLoadingText: opts.submitLoadingText || "Salvando..." });
    try {
      updateLoadingStep(1, "active", {
        messages: { 1: "Validando dados...", 4: "Salvando alterações..." },
      });
      updateLoadingStep(1, "completed");
      updateLoadingStep(4, "active");

      const formData = new FormData(form);
      const resp = await fetch(form.action || window.location.href, {
        method: "POST",
        body: formData,
      });

      if (resp.ok) {
        updateLoadingStep(4, "completed");
        hideLoading();
        showSuccess(
          opts.successTitle || "Salvo com sucesso! ✅",
          opts.successMessage || "Alterações salvas."
        );
        setTimeout(() => {
          window.location.href =
            opts.redirectUrl || resp.url || window.location.href;
        }, 1200);
      } else {
        const text = await resp.text();
        throw new Error(text || `Erro HTTP ${resp.status}`);
      }
    } catch (err) {
      hideLoading();
      const msg = String(err?.message || err);
      showError("Erro ao salvar", msg);
    }
  });
}
window.registerSimpleFormSubmit = registerSimpleFormSubmit;

/**
 * Submissão com validações completas do Telegram (mesmo fluxo do create):
 * - valida planos, token, ids de grupo
 * - valida bot nos grupos (VIP e logs) via Telegram API
 * - envia formulário com fetch e mostra feedback
 *
 * opts: {
 *   formSelector?: string,
 *   successTitle?: string,
 *   successMessage?: string,
 *   redirectUrl?: string,
 *   submitLoadingText?: string (default 'Validando...')
 * }
 */
function registerBotSubmitWithTelegramChecks(opts = {}) {
  const form = document.querySelector(opts.formSelector || "form.bot-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const submitBtn = document.getElementById(FormUtilsConfig.submitBtnId);
    if (submitBtn?.disabled) return;

    // 1) Validação de planos
    const planCheck = validatePlanSection({
      pixSelector: 'input[name="pix_values[]"]',
      nameSelector: 'input[name="plan_names[]"]',
      durationSelector: 'select[name="plan_duration[]"]',
    });
    if (!planCheck.ok) {
      showError(planCheck.title, planCheck.message);
      return;
    }

    // 2) Token e grupos
    const token = document.getElementById("token")?.value?.trim();
    if (!validateTelegramToken(token)) {
      showError(
        "Token Inválido",
        "Token do bot inválido! Verifique se copiou corretamente do @BotFather."
      );
      return;
    }
    const idVip = document.getElementById("id_vip")?.value?.trim();
    const idLogs = document.getElementById("id_logs")?.value?.trim();
    if (!validateGroupId(idVip)) {
      showError(
        "Grupo VIP Inválido",
        "O ID do Grupo VIP deve começar com '-' (ex: -1001234567890)"
      );
      return;
    }
    if (!validateGroupId(idLogs)) {
      showError(
        "Grupo de Notificações Inválido",
        "O ID do Grupo de Notificações deve começar com '-' (ex: -1001234567890)"
      );
      return;
    }

    // 3) Loading + validação no Telegram
    showLoading({
      submitLoadingText: opts.submitLoadingText || "Validando...",
    });
    try {
      const stepMessages = (opts && opts.stepMessages) || {
        1: "Verificando se o token é válido...",
        2: "Testando acesso ao grupo VIP como admin...",
        3: "Testando acesso ao grupo de notificações como admin...",
        4: "Salvando alterações...",
      };
      updateLoadingStep(1, "active", { messages: stepMessages });
      await validateBotInGroups(token, idVip, idLogs);
      updateLoadingStep(1, "completed");

      // 4) Envia formulário
      updateLoadingStep(4, "active", { messages: stepMessages });
      const formData = new FormData(form);
      const resp = await fetch(form.action || window.location.href, {
        method: "POST",
        body: formData,
      });
      if (resp.ok) {
        updateLoadingStep(4, "completed", { messages: stepMessages });
        hideLoading();
        showSuccess(
          opts.successTitle || "Salvo com sucesso! ✅",
          opts.successMessage || "Alterações salvas."
        );
        setTimeout(() => {
          window.location.href =
            opts.redirectUrl || resp.url || window.location.href;
        }, 1200);
      } else {
        const text = await resp.text();
        throw new Error(text || `Erro HTTP ${resp.status}`);
      }
    } catch (err) {
      hideLoading();
      const msg = String(err?.message || err);
      let title = "Erro ao validar";
      let message = msg;
      if (msg.includes("Token inválido")) {
        title = "Token Inválido";
        message =
          "O token do bot é inválido ou expirou. Verifique e tente novamente.";
      } else if (msg.toLowerCase().includes("vip")) {
        title = "Problema no Grupo VIP";
        message = `Verifique se o bot está no grupo VIP e é administrador (${idVip}).`;
      } else if (msg.toLowerCase().includes("notific")) {
        title = "Problema no Grupo de Notificações";
        message = `Verifique se o bot está no grupo de notificações e é administrador (${idLogs}).`;
      }
      showError(title, message);
    }
  });
}
window.registerBotSubmitWithTelegramChecks =
  registerBotSubmitWithTelegramChecks;
