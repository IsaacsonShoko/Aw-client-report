document.addEventListener('DOMContentLoaded', () => {
    const inputs = document.querySelectorAll('.calc-input');
    const useLastButtons = document.querySelectorAll('.use-last-btn');
    
    function formatCurrency(val) {
        return '$' + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function calculate() {
        // 1. Trust Value
        const trustInput = document.querySelector('.calc-trust');
        const trustVal = trustInput ? (parseFloat(trustInput.value) || 0) : 0;
        const trustEl = document.getElementById('live-trust');
        if (trustEl) trustEl.innerText = formatCurrency(trustVal);

        // 2. Accounts
        const accInputs = document.querySelectorAll('.calc-account');
        let nonRetTotal = 0;
        let retTotals = {};

        accInputs.forEach(inp => {
            const val = parseFloat(inp.value) || 0;
            const cat = inp.getAttribute('data-category');
            const pid = inp.getAttribute('data-person');

            if (cat === 'non_retirement') {
                nonRetTotal += val;
            } else if (cat === 'retirement') {
                if (!retTotals[pid]) retTotals[pid] = 0;
                retTotals[pid] += val;
            }
        });

        const nonRetEl = document.getElementById('live-non-ret');
        if (nonRetEl) nonRetEl.innerText = formatCurrency(nonRetTotal);

        let totalRet = 0;
        for (const [pid, val] of Object.entries(retTotals)) {
            const el = document.getElementById(`live-ret-${pid}`);
            if (el) el.innerText = formatCurrency(val);
            totalRet += val;
        }

        // 3. Grand Total (Net Worth)
        const netWorth = totalRet + nonRetTotal + trustVal;
        const netWorthEl = document.getElementById('live-net-worth');
        if (netWorthEl) netWorthEl.innerText = formatCurrency(netWorth);

        // 4. Liabilities
        const liabInputs = document.querySelectorAll('.calc-liability');
        let liabTotal = 0;
        liabInputs.forEach(inp => {
            liabTotal += (parseFloat(inp.value) || 0);
        });
        const liabEl = document.getElementById('live-liab');
        if (liabEl) liabEl.innerText = formatCurrency(liabTotal);

        // UI updates for highlighted incomplete fields
        inputs.forEach(inp => {
            if (inp.value.trim() === "") {
                inp.classList.add('highlight');
            } else {
                inp.classList.remove('highlight');
            }
        });
    }

    inputs.forEach(inp => {
        inp.addEventListener('input', calculate);
    });

    useLastButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const target = document.querySelector(`[name="${button.dataset.target}"]`);
            if (!target) return;
            target.value = button.dataset.value;
            target.dispatchEvent(new Event('input', { bubbles: true }));
        });
    });

    // Initial calc
    calculate();
});
