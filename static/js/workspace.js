(() => {
    'use strict';

    const app = document.getElementById('workspace-app');
    if (!app) return;

    const SERMON_ID = Number(app.dataset.sermonId);
    const CSRF_TOKEN = app.dataset.csrfToken || '';
    const researchNotes = JSON.parse(document.getElementById('initial-research').textContent || '[]');
    const initialOutline = JSON.parse(document.getElementById('initial-outline').textContent || '{}');
    let lastRaw = '';
    let lastHtml = '';
    let lastType = '';
    let saveTimer = null;
    let passageTimer = null;
    let bibleCatalog = [];

    const $ = (id) => document.getElementById(id);

    function apiHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF_TOKEN,
        };
    }

    function showTab(tab) {
        document.querySelectorAll('.tab-btn').forEach((button) => {
            button.classList.toggle('active', button.dataset.tab === tab);
        });
        $('tab-research').classList.toggle('active', tab === 'research');
        $('tab-outline').classList.toggle('active', tab === 'outline');
    }

    function makeField(labelText, field, value = '', rows = 0, placeholder = '') {
        const group = document.createElement('div');
        group.className = 'form-group';
        const label = document.createElement('label');
        label.textContent = labelText;
        group.appendChild(label);
        const control = rows > 0 ? document.createElement('textarea') : document.createElement('input');
        if (rows > 0) control.rows = rows;
        else control.type = 'text';
        control.dataset.field = field;
        control.value = value || '';
        if (placeholder) control.placeholder = placeholder;
        control.addEventListener('input', scheduleSave);
        group.appendChild(control);
        return group;
    }

    function addPoint(data = {}) {
        const point = document.createElement('div');
        point.className = 'sermon-point';
        point.appendChild(makeField('Título do tópico', 'titulo', data.titulo, 0, 'Movimento do texto'));
        point.appendChild(makeField('Texto base', 'texto_base', data.texto_base, 0, 'Verso(s) que sustentam o ponto'));
        point.appendChild(makeField('Elucidação / Explicação', 'explicacao', data.explicacao, 5));
        point.appendChild(makeField('Ilustração', 'ilustracao', data.ilustracao, 3));
        point.appendChild(makeField('Aplicação', 'aplicacao', data.aplicacao, 4));
        point.appendChild(makeField('Transição', 'transicao', data.transicao, 2));

        const actions = document.createElement('div');
        actions.className = 'point-actions';
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'btn-link-danger';
        remove.textContent = 'Excluir tópico';
        remove.addEventListener('click', () => {
            point.remove();
            scheduleSave();
        });
        actions.appendChild(remove);
        point.appendChild(actions);
        $('points-container').appendChild(point);
    }

    function collectOutline() {
        const topicos = [...document.querySelectorAll('.sermon-point')].map((el) => ({
            titulo: el.querySelector('[data-field="titulo"]').value,
            texto_base: el.querySelector('[data-field="texto_base"]').value,
            explicacao: el.querySelector('[data-field="explicacao"]').value,
            ilustracao: el.querySelector('[data-field="ilustracao"]').value,
            aplicacao: el.querySelector('[data-field="aplicacao"]').value,
            transicao: el.querySelector('[data-field="transicao"]').value,
        }));
        return {
            ict: $('ict').value,
            tese: $('tese').value,
            fcd: $('fcd').value,
            proposito_redentivo: $('proposito-redentivo').value,
            proposito_basico: $('prop-basico').value,
            proposito_especifico: $('prop-especifico').value,
            intro: $('intro').value,
            topicos,
            conexao_cristocentrica: $('conexao-cristocentrica').value,
            conclusao: $('conclusao').value,
        };
    }

    function scheduleSave() {
        $('autosave-indicator').textContent = 'Alterações pendentes…';
        clearTimeout(saveTimer);
        saveTimer = setTimeout(saveSermon, 900);
    }

    async function saveSermon() {
        $('autosave-indicator').textContent = 'Salvando…';
        try {
            const response = await fetch(`/api/sermons/${SERMON_ID}`, {
                method: 'PATCH',
                headers: apiHeaders(),
                body: JSON.stringify({
                    reference: $('bible-ref').value,
                    research_notes: researchNotes,
                    outline: collectOutline(),
                }),
            });
            if (!response.ok) throw new Error('save failed');
            $('autosave-indicator').textContent = `Salvo às ${new Date().toLocaleTimeString('pt-BR')}`;
        } catch (_error) {
            $('autosave-indicator').textContent = 'Erro ao salvar';
        }
    }

    async function analyze(type) {
        const reference = $('bible-ref').value.trim();
        if (!reference) {
            window.alert('Digite a referência bíblica.');
            return;
        }
        $('loading').hidden = false;
        $('ai-output').classList.add('is-loading');
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: apiHeaders(),
                body: JSON.stringify({texto: reference, tipo: type}),
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                $('ai-output').textContent = data.error || 'Não foi possível concluir a análise.';
                return;
            }
            $('ai-output').innerHTML = data.html;
            lastRaw = data.markdown || '';
            lastHtml = data.html || '';
            lastType = type;
        } catch (_error) {
            $('ai-output').textContent = 'Erro de conexão.';
        } finally {
            $('loading').hidden = true;
            $('ai-output').classList.remove('is-loading');
        }
    }

    function incorporate() {
        if (!lastRaw) return;
        researchNotes.push({tipo: lastType, markdown: lastRaw});
        const item = document.createElement('div');
        item.className = 'note-item';
        const tag = document.createElement('span');
        tag.className = 'note-tag';
        tag.textContent = `[${lastType}]`;
        const body = document.createElement('div');
        body.className = 'note-body';
        body.innerHTML = lastHtml;
        item.append(tag, body);
        $('staged-content').appendChild(item);
        $('staged-content').scrollTop = $('staged-content').scrollHeight;
        scheduleSave();
    }

    function applySuggestion(data) {
        $('ict').value = data.ict || '';
        $('tese').value = data.tese || '';
        $('fcd').value = data.fcd || '';
        $('proposito-redentivo').value = data.proposito_redentivo || '';
        $('prop-basico').value = data.proposito_basico || '';
        $('prop-especifico').value = data.proposito_especifico || '';
        $('intro').value = data.intro || '';
        $('conexao-cristocentrica').value = data.conexao_cristocentrica || '';
        $('conclusao').value = data.conclusao || '';
        $('points-container').replaceChildren();
        const points = Array.isArray(data.topicos) && data.topicos.length ? data.topicos : [{}];
        points.forEach(addPoint);
        scheduleSave();
    }

    async function suggestSermon() {
        const notesText = researchNotes.map((note) => `[${note.tipo}]\n${note.markdown}`).join('\n\n');
        if (notesText.trim().length < 50 && !window.confirm('Há poucas notas de pesquisa. Deseja continuar?')) return;
        const button = $('suggest-sermon');
        button.disabled = true;
        button.textContent = 'Estruturando sermão…';
        try {
            const response = await fetch('/api/suggest_sermon', {
                method: 'POST',
                headers: apiHeaders(),
                body: JSON.stringify({notes: notesText, reference: $('bible-ref').value}),
            });
            const data = await response.json();
            if (!response.ok || data.error) {
                window.alert(data.error || 'A IA não retornou uma estrutura válida.');
                return;
            }
            applySuggestion(data);
        } catch (_error) {
            window.alert('Erro de conexão ao gerar o esboço.');
        } finally {
            button.disabled = false;
            button.textContent = '✨ Sugestão da IA';
        }
    }

    async function fetchPassage() {
        const reference = $('bible-ref').value.trim();
        const panel = $('passage-panel');
        if (!reference) {
            panel.hidden = true;
            return;
        }
        try {
            const query = new URLSearchParams({ref: reference, sermon_id: String(SERMON_ID)});
            const response = await fetch(`/api/passage?${query.toString()}`);
            const data = await response.json();
            if (!response.ok || !data || !data.text) {
                panel.hidden = true;
                return;
            }
            panel.replaceChildren();
            const version = document.createElement('span');
            version.className = 'version-tag';
            version.textContent = `${data.version || ''}${data.cached ? ' · cache' : ''}`;
            const text = document.createElement('div');
            text.className = 'passage-text';
            text.textContent = data.text;
            panel.append(version, text);
            panel.hidden = false;
        } catch (_error) {
            panel.hidden = true;
        }
    }

    function resetSelect(select, placeholder) {
        select.replaceChildren();
        const option = document.createElement('option');
        option.value = '';
        option.textContent = placeholder;
        select.appendChild(option);
    }

    async function loadBibleCatalog() {
        const status = $('bible-picker-status');
        try {
            const response = await fetch('/api/bible/catalog');
            const data = await response.json();
            if (!response.ok || !Array.isArray(data.books)) throw new Error('catalog');
            bibleCatalog = data.books;
            resetSelect($('bible-book'), 'Selecione…');
            bibleCatalog.forEach((book) => {
                const option = document.createElement('option');
                option.value = book.abbr;
                option.textContent = book.name;
                option.dataset.chapters = String(book.chapters);
                $('bible-book').appendChild(option);
            });
            status.textContent = `Versão de consulta: ${data.version || 'NVI'}`;
        } catch (_error) {
            status.textContent = 'A seleção guiada está temporariamente indisponível; o campo livre continua funcionando.';
        }
    }

    function populateChapters() {
        const book = bibleCatalog.find((item) => item.abbr === $('bible-book').value);
        resetSelect($('bible-chapter'), 'Capítulo…');
        resetSelect($('bible-verse-start'), 'Todos');
        resetSelect($('bible-verse-end'), '—');
        $('bible-verse-start').disabled = true;
        $('bible-verse-end').disabled = true;
        $('apply-bible-selection').disabled = true;
        if (!book) {
            $('bible-chapter').disabled = true;
            return;
        }
        for (let chapter = 1; chapter <= book.chapters; chapter += 1) {
            const option = document.createElement('option');
            option.value = String(chapter);
            option.textContent = String(chapter);
            $('bible-chapter').appendChild(option);
        }
        $('bible-chapter').disabled = false;
    }

    async function populateVerses() {
        const book = $('bible-book').value;
        const chapter = $('bible-chapter').value;
        resetSelect($('bible-verse-start'), 'Todos');
        resetSelect($('bible-verse-end'), '—');
        $('bible-verse-start').disabled = true;
        $('bible-verse-end').disabled = true;
        $('apply-bible-selection').disabled = !book || !chapter;
        if (!book || !chapter) return;
        $('bible-picker-status').textContent = 'Carregando versículos…';
        try {
            const query = new URLSearchParams({book, chapter});
            const response = await fetch(`/api/bible/chapter?${query.toString()}`);
            const data = await response.json();
            if (!response.ok || !Array.isArray(data.verses)) throw new Error('chapter');
            data.verses.forEach((verse) => {
                for (const select of [$('bible-verse-start'), $('bible-verse-end')]) {
                    const option = document.createElement('option');
                    option.value = String(verse.number);
                    option.textContent = String(verse.number);
                    select.appendChild(option);
                }
            });
            $('bible-verse-start').disabled = false;
            $('bible-verse-end').disabled = false;
            $('bible-picker-status').textContent = `Capítulo carregado · ${data.version || 'NVI'}`;
        } catch (_error) {
            $('bible-picker-status').textContent = 'Não foi possível carregar os versículos; ainda é possível selecionar o capítulo inteiro.';
        }
    }

    function applyBibleSelection() {
        const book = bibleCatalog.find((item) => item.abbr === $('bible-book').value);
        const chapter = $('bible-chapter').value;
        if (!book || !chapter) return;
        const start = $('bible-verse-start').value;
        const end = $('bible-verse-end').value;
        let reference = `${book.name} ${chapter}`;
        if (start) {
            reference += `:${start}`;
            if (end && Number(end) >= Number(start) && end !== start) reference += `-${end}`;
        }
        $('bible-ref').value = reference;
        scheduleSave();
        fetchPassage();
    }

    document.querySelectorAll('[data-show-tab]').forEach((button) => {
        button.addEventListener('click', () => showTab(button.dataset.showTab));
    });
    document.querySelectorAll('[data-analysis-type]').forEach((button) => {
        button.addEventListener('click', () => analyze(button.dataset.analysisType));
    });
    $('incorporate-note').addEventListener('click', incorporate);
    $('suggest-sermon').addEventListener('click', suggestSermon);
    $('add-point').addEventListener('click', () => {
        addPoint({});
        scheduleSave();
    });
    document.querySelectorAll('[data-save-field]').forEach((control) => {
        control.addEventListener('input', scheduleSave);
        control.addEventListener('change', scheduleSave);
    });
    $('bible-ref').addEventListener('input', () => {
        scheduleSave();
        clearTimeout(passageTimer);
        passageTimer = setTimeout(fetchPassage, 700);
    });
    $('bible-book').addEventListener('change', populateChapters);
    $('bible-chapter').addEventListener('change', populateVerses);
    $('bible-verse-start').addEventListener('change', () => {
        const start = Number($('bible-verse-start').value || 0);
        [...$('bible-verse-end').options].forEach((option) => {
            option.disabled = Boolean(option.value) && Number(option.value) < start;
        });
    });
    $('apply-bible-selection').addEventListener('click', applyBibleSelection);

    const initialPoints = Array.isArray(initialOutline.topicos) && initialOutline.topicos.length ? initialOutline.topicos : [{}];
    initialPoints.forEach(addPoint);
    loadBibleCatalog();
    if ($('bible-ref').value) fetchPassage();
})();
