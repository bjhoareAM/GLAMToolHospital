const steps = Array.from(document.querySelectorAll(".form-step"));
const nextButtons = Array.from(document.querySelectorAll(".next-step"));
const previousButtons = Array.from(document.querySelectorAll(".previous-step"));
const currentStepNumber = document.getElementById("currentStepNumber");
const totalStepNumber = document.getElementById("totalStepNumber");
const wikiUsernameInput = document.getElementById("wiki_username");

const projectTagSelect = document.getElementById("project_tag");
const otherToolFields = document.getElementById("other-tool-fields");
const toolNameInput = document.getElementById("tool_name");
const toolUrlInput = document.getElementById("tool_url");

let currentStep = 0;

if (totalStepNumber) {
    totalStepNumber.textContent = steps.length;
}

function showStep(index) {
    steps.forEach((step, stepIndex) => {
        step.classList.toggle("active", stepIndex === index);
    });

    if (currentStepNumber) {
        currentStepNumber.textContent = index + 1;
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

function validateCurrentStep() {
    if (!steps[currentStep]) {
        return true;
    }

    const currentFields = Array.from(
        steps[currentStep].querySelectorAll("input, select, textarea")
    );

    for (const field of currentFields) {
        if (!field.checkValidity()) {
            field.reportValidity();
            return false;
        }
    }

    return true;
}

function updateOtherToolFields() {
    if (!projectTagSelect || !otherToolFields) {
        return;
    }

    const showFields = projectTagSelect.value === "other";
    otherToolFields.hidden = !showFields;

    if (!showFields) {
        if (toolNameInput) {
            toolNameInput.value = "";
        }

        if (toolUrlInput) {
            toolUrlInput.value = "";
        }
    }
}

if (projectTagSelect && otherToolFields) {
    projectTagSelect.addEventListener("change", updateOtherToolFields);
    updateOtherToolFields();
}

nextButtons.forEach((button) => {
    button.addEventListener("click", () => {
        if (!validateCurrentStep()) {
            return;
        }

        if (currentStep < steps.length - 1) {
            currentStep += 1;
            showStep(currentStep);
        }
    });
});

previousButtons.forEach((button) => {
    button.addEventListener("click", () => {
        if (currentStep > 0) {
            currentStep -= 1;
            showStep(currentStep);
        }
    });
});

if (wikiUsernameInput) {
    function removeUserPrefix() {
        wikiUsernameInput.value = wikiUsernameInput.value.replace(/^\s*user:\s*/i, "");
    }

    wikiUsernameInput.addEventListener("input", removeUserPrefix);
    wikiUsernameInput.addEventListener("blur", removeUserPrefix);
}

if (steps.length > 0) {
    showStep(currentStep);
}