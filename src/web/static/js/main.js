// GEO 品牌监测 - 主应用逻辑

let currentProjectId = null;
let currentProjectName = '';
let trendChart = null;
let positionChart = null;

// 页面加载
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
});

// ========== 项目管理 ==========

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();

        if (data.success) {
            renderProjectList(data.projects);

            if (data.default_project_id && data.projects.length > 0) {
                const defaultProject = data.projects.find(p => p.id === data.default_project_id);
                if (defaultProject) {
                    selectProject(defaultProject.id, defaultProject.name, defaultProject.description);
                } else {
                    selectProject(data.projects[0].id, data.projects[0].name, data.projects[0].description);
                }
            } else if (data.projects.length > 0) {
                selectProject(data.projects[0].id, data.projects[0].name, data.projects[0].description);
            }
        }
    } catch (error) {
        console.error('加载项目失败:', error);
    }
}

function renderProjectList(projects) {
    const container = document.getElementById('projectList');

    if (!projects || projects.length === 0) {
        container.innerHTML = `
            <div class="empty-state-small">
                <p>暂无项目</p>
            </div>
        `;
        return;
    }

    container.innerHTML = projects.map(project => `
        <div class="project-item" id="project-${project.id}" onclick="selectProject(${project.id}, '${escapeHtml(project.name)}', '${escapeHtml(project.description)}')">
            <div class="project-item-name">${escapeHtml(project.name)}</div>
            ${project.description ? `<div class="project-item-desc">${escapeHtml(project.description)}</div>` : ''}
        </div>
    `).join('');
}

function selectProject(projectId, name, description) {
    currentProjectId = projectId;
    currentProjectName = name;
    currentDate = null;

    document.querySelectorAll('.project-item').forEach(el => el.classList.remove('active'));
    const el = document.getElementById(`project-${projectId}`);
    if (el) el.classList.add('active');

    document.getElementById('noProjectSelected').style.display = 'none';
    document.getElementById('projectContent').style.display = 'block';

    document.getElementById('currentProjectName').textContent = name;
    document.getElementById('currentProjectDesc').textContent = description || '';
    document.getElementById('projectBrandName').textContent = name;

    // 重置所有视图状态
    document.getElementById('taskSection').style.display = 'none';
    document.getElementById('taskDetailSection').style.display = 'none';
    document.getElementById('detailSection').style.display = 'none';

    showView('control');
    initControlView();
}

function showCreateProjectDialog() {
    document.getElementById('newProjectName').value = '';
    document.getElementById('newProjectDesc').value = '';
    document.getElementById('createProjectModal').style.display = 'flex';
}

function closeCreateProjectDialog() {
    document.getElementById('createProjectModal').style.display = 'none';
}

async function createProject() {
    const name = document.getElementById('newProjectName').value.trim();
    const desc = document.getElementById('newProjectDesc').value.trim();

    if (!name) {
        alert('请输入项目名称');
        return;
    }

    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, description: desc})
        });
        const data = await response.json();

        if (data.success) {
            closeCreateProjectDialog();
            loadProjects();
            selectProject(data.project_id, name, desc);
        } else {
            alert('创建失败: ' + data.error);
        }
    } catch (error) {
        console.error('创建项目失败:', error);
        alert('创建失败');
    }
}

// ========== 视图切换 ==========

function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    document.getElementById(viewName + 'View').classList.add('active');
    const navBtn = document.querySelector(`.nav-btn[onclick="showView('${viewName}')"]`);
    if (navBtn) navBtn.classList.add('active');

    if (!currentProjectId) return;

    if (viewName === 'dashboard') {
        initDashboardView();
    } else if (viewName === 'files') {
        initFilesView();
    } else if (viewName === 'control') {
        initControlView();
    }
}

// ========== 仪表盘视图 ==========

function initDashboardView() {
    initCharts();
    loadSummary();
    loadTrend();
    loadPositionDistribution();
}

function initCharts() {
    if (!trendChart) {
        const trendDom = document.getElementById('trendChart');
        trendChart = echarts.init(trendDom);
    }

    if (!positionChart) {
        const positionDom = document.getElementById('positionChart');
        positionChart = echarts.init(positionDom);
    }

    window.addEventListener('resize', () => {
        trendChart && trendChart.resize();
        positionChart && positionChart.resize();
    });
}

async function loadSummary() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/summary`);
        const data = await response.json();

        const summaries = data.summaries || [];
        const dates = data.available_dates || [];

        document.getElementById('totalDays').textContent = dates.length;

        let totalQuestions = 0;
        let totalMentionCount = 0;
        summaries.forEach(s => {
            totalQuestions += s.total_questions || 0;
            totalMentionCount += s.brand_mentioned_count || 0;
        });

        const avgRate = totalQuestions > 0 ? Math.round((totalMentionCount / totalQuestions) * 100) : 0;
        document.getElementById('mentionRate').textContent = avgRate + '%';
        document.getElementById('totalQuestions').textContent = totalQuestions;

        renderDateList(dates, summaries);
    } catch (error) {
        console.error('加载汇总数据失败:', error);
    }
}

async function loadTrend() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/trend`);
        const data = await response.json();
        renderTrendChart(data.stats);
    } catch (error) {
        console.error('加载趋势数据失败:', error);
    }
}

async function loadPositionDistribution() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/position/distribution`);
        const data = await response.json();
        if (data.success) {
            renderPositionChart(data.primary_position || {}, data.primary_brand);
        }
    } catch (error) {
        console.error('加载位置分布失败:', error);
    }
}

function renderDateList(dates, summaries) {
    const container = document.getElementById('dateList');

    if (!dates || dates.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>暂无数据</p>
            </div>
        `;
        return;
    }

    container.innerHTML = dates.map(date => {
        const summary = summaries.find(s => s.date_str === date);
        const mentionCount = summary?.brand_mentioned_count || 0;
        const totalQ = summary?.total_questions || 0;
        const rate = totalQ > 0 ? Math.round((mentionCount / totalQ) * 100) : 0;

        return `
            <div class="date-item" onclick="showDetail('${date}')">
                <div class="date-item-title">${formatDate(date)}</div>
                <div class="date-item-meta">提及率: ${rate}% | ${totalQ}个问题</div>
            </div>
        `;
    }).join('');
}

function renderTrendChart(stats) {
    if (!trendChart) return;

    const dates = stats.map(s => formatDate(s.date_str));
    const mentionRates = stats.map(s => {
        const q = s.question_count || 0;
        const m = s.mention_count || 0;
        return q > 0 ? Math.round((m / q) * 100) : 0;
    });

    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: (params) => {
                const p = params[0];
                return `${p.name}<br/>提及率: ${p.value}%`;
            }
        },
        grid: {left: '3%', right: '4%', bottom: '3%', containLabel: true},
        xAxis: {type: 'category', boundaryGap: false, data: dates},
        yAxis: {type: 'value', min: 0, max: 100, axisLabel: {formatter: '{value}%'}},
        series: [{
            name: '提及率',
            type: 'line',
            smooth: true,
            data: mentionRates,
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    {offset: 0, color: 'rgba(102, 126, 234, 0.3)'},
                    {offset: 1, color: 'rgba(102, 126, 234, 0.05)'}
                ])
            },
            lineStyle: {color: '#667eea', width: 2},
            itemStyle: {color: '#667eea'}
        }]
    };

    trendChart.setOption(option, true);
}

function renderPositionChart(positionData, brandName) {
    if (!positionChart) return;

    const positionLabels = {'first': '开头', 'middle': '中间', 'last': '结尾'};
    const categories = [];
    const values = [];

    for (const pos in positionData) {
        categories.push(positionLabels[pos] || pos);
        values.push(positionData[pos]);
    }

    const option = {
        tooltip: {trigger: 'item', confine: true},
        legend: {orient: 'horizontal', bottom: 10, left: 'center'},
        series: [{
            name: '出现次数',
            type: 'pie',
            radius: ['35%', '55%'],
            center: ['50%', '48%'],
            avoidLabelOverlap: true,
            itemStyle: {borderRadius: 6, borderColor: '#fff', borderWidth: 2},
            label: {show: true, position: 'outside', formatter: '{b}\n{c}次 ({d}%)', lineHeight: 20, fontSize: 12},
            labelLine: {show: true, length: 20, length2: 25, smooth: true},
            emphasis: {label: {show: true, fontSize: 14, fontWeight: 'bold'}, scale: true, scaleSize: 8},
            data: categories.map((cat, i) => ({value: values[i], name: cat}))
        }]
    };

    positionChart.setOption(option, true);
}

async function showDetail(dateStr) {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/daily/${dateStr}`);
        const data = await response.json();

        document.getElementById('detailSection').style.display = 'block';
        document.getElementById('detailDate').textContent = formatDate(dateStr);

        const container = document.getElementById('detailContent');

        if (!data.tasks || data.tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>当天暂无数据</p>
                </div>
            `;
            return;
        }

        container.innerHTML = data.tasks.map(taskData => {
            const task = taskData.task;
            const questions = taskData.questions;
            return `
                <div class="detail-item">
                    <div class="detail-item-header">
                        <span class="detail-hour">${task.hour}:00</span>
                    </div>
                    <div class="detail-question-list">
                        ${questions.map(q => `
                            <div class="detail-question">
                                <div class="detail-question-title">Q: ${escapeHtml(q.question_text)}</div>
                                <div class="detail-question-response">A: ${escapeHtml(q.response_text || '(无回复)').substring(0, 300)}${(q.response_text || '').length > 300 ? '...' : ''}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }).join('');

        document.getElementById('detailSection').scrollIntoView({behavior: 'smooth'});
    } catch (error) {
        console.error('加载详情失败:', error);
    }
}

function hideDetail() {
    document.getElementById('detailSection').style.display = 'none';
}

// ========== 文件浏览视图 ==========

function initFilesView() {
    // 重置视图状态
    document.getElementById('taskSection').style.display = 'none';
    document.getElementById('taskDetailSection').style.display = 'none';
    currentDate = null;
    // 重新加载日期列表
    loadFileDateList();
}

async function loadFileDateList() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/summary`);
        const data = await response.json();
        const dates = data.available_dates || [];

        const container = document.getElementById('fileDateList');

        if (!dates || dates.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>暂无数据</p>
                </div>
            `;
            return;
        }

        container.innerHTML = dates.map(date => `
            <div class="date-item" onclick="showTaskList('${date}')">
                <div class="date-item-title">${formatDate(date)}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('加载日期列表失败:', error);
    }
}

async function showTaskList(dateStr) {
    if (!currentProjectId) return;

    currentDate = dateStr;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/date/${dateStr}/tasks`);
        const data = await response.json();

        if (!data.success) {
            alert('加载失败: ' + data.error);
            return;
        }

        document.getElementById('taskDate').textContent = formatDate(dateStr);
        document.getElementById('taskSection').style.display = 'block';
        document.getElementById('taskDetailSection').style.display = 'none';

        const container = document.getElementById('taskList');

        if (!data.tasks || data.tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>当天暂无任务</p>
                </div>
            `;
            return;
        }

        container.innerHTML = data.tasks.map(task => `
            <div class="task-item" onclick="showTaskDetail('${task.folder}')">
                <div class="task-item-title">${escapeHtml(task.folder)}</div>
                <div class="task-item-question">${escapeHtml(task.question)}</div>
            </div>
        `).join('');

        document.getElementById('taskSection').scrollIntoView({behavior: 'smooth'});
    } catch (error) {
        console.error('加载任务列表失败:', error);
    }
}

function backToDateList() {
    document.getElementById('taskSection').style.display = 'none';
    document.getElementById('taskDetailSection').style.display = 'none';
}

async function showTaskDetail(taskFolder) {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/date/${currentDate}/task/${encodeURIComponent(taskFolder)}/detail`);
        const data = await response.json();

        if (!data.success) {
            alert('加载失败: ' + data.error);
            return;
        }

        document.getElementById('taskTitle').textContent = data.task_folder;
        document.getElementById('taskSection').style.display = 'none';
        document.getElementById('taskDetailSection').style.display = 'block';

        const reportSection = document.getElementById('reportSection');
        if (data.report_content) {
            reportSection.style.display = 'block';
            document.getElementById('reportContent').innerHTML = marked.parse(data.report_content);
        } else {
            reportSection.style.display = 'none';
        }

        const answersList = document.getElementById('answersList');
        if (!data.answer_files || data.answer_files.length === 0) {
            answersList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>暂无回答</p>
                </div>
            `;
        } else {
            answersList.innerHTML = data.answer_files.map((file, idx) => {
                let label = file;
                if (file === '豆包回答.md') {
                    label = '豆包回答';
                } else {
                    label = file.replace('_豆包回答.md', '');
                }
                return `
                    <div class="answer-item" id="answer-${idx}">
                        <div class="answer-header">
                            <span class="answer-time">💬 ${label}</span>
                            <button class="expand-btn" onclick="toggleAnswer('${currentDate}', '${taskFolder}', '${file}', ${idx})">展开查看</button>
                        </div>
                        <div class="answer-preview">点击"展开查看"查看完整内容</div>
                        <div class="answer-full" id="answer-full-${idx}"></div>
                    </div>
                `;
            }).join('');
        }

        document.getElementById('taskDetailSection').scrollIntoView({behavior: 'smooth'});
    } catch (error) {
        console.error('加载任务详情失败:', error);
    }
}

async function toggleAnswer(dateStr, taskFolder, answerFile, idx) {
    if (!currentProjectId) return;

    const fullDiv = document.getElementById(`answer-full-${idx}`);
    const btn = document.querySelector(`#answer-${idx} .expand-btn`);

    if (fullDiv.classList.contains('expanded')) {
        fullDiv.classList.remove('expanded');
        btn.textContent = '展开查看';
        return;
    }

    if (fullDiv.innerHTML.trim()) {
        fullDiv.classList.add('expanded');
        btn.textContent = '收起';
        return;
    }

    try {
        btn.textContent = '加载中...';
        const response = await fetch(`/api/projects/${currentProjectId}/date/${dateStr}/task/${encodeURIComponent(taskFolder)}/answer/${encodeURIComponent(answerFile)}`);
        const data = await response.json();

        if (!data.success) {
            alert('加载失败: ' + data.error);
            btn.textContent = '展开查看';
            return;
        }

        fullDiv.innerHTML = `<div class="markdown-body">${marked.parse(data.content)}</div>`;
        fullDiv.classList.add('expanded');
        btn.textContent = '收起';
    } catch (error) {
        console.error('加载回答详情失败:', error);
        btn.textContent = '展开查看';
    }
}

function backToTaskList() {
    document.getElementById('taskDetailSection').style.display = 'none';
    document.getElementById('taskSection').style.display = 'block';
}

// ========== 任务控制视图 ==========

let currentTasks = [];
let editingTaskIdx = -1;

function initControlView() {
    loadTaskList();
    loadSchedule();
    loadSchedulerStatus();
    startStatusPolling();
    setInterval(loadSchedulerStatus, 10000);
}

async function loadTaskList() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/config/tasks`);
        const data = await response.json();

        if (data.success) {
            currentTasks = data.tasks || [];
            if (data.project_name) {
                document.getElementById('projectBrandName').textContent = data.project_name;
            }
            renderTaskList();
        }
    } catch (error) {
        console.error('加载任务列表失败:', error);
    }
}

function renderTaskList() {
    const container = document.getElementById('taskManageList');

    if (!currentTasks || currentTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>暂无任务</p>
                <p>点击右上角"添加任务"来创建第一个任务</p>
            </div>
        `;
        return;
    }

    container.innerHTML = currentTasks.map((task, idx) => `
        <div class="task-item">
            <div class="task-item-title">任务${idx + 1}</div>
            <div class="task-item-question">问题: ${escapeHtml(task.question)}</div>
            <div class="task-item-question">品牌: ${escapeHtml(task.brands.join('; '))}</div>
            <div class="task-item-actions">
                <button class="btn-edit" onclick="editTask(${idx})">✏️ 编辑</button>
                <button class="btn-delete" onclick="deleteTask(${idx})">🗑️ 删除</button>
            </div>
        </div>
    `).join('');
}

function showAddTaskDialog() {
    editingTaskIdx = -1;
    document.getElementById('taskModalTitle').textContent = '添加监测任务';
    document.getElementById('taskQuestion').value = '';
    document.getElementById('taskBrands').value = currentProjectName;
    document.getElementById('taskModal').style.display = 'flex';
}

function editTask(idx) {
    editingTaskIdx = idx;
    const task = currentTasks[idx];
    document.getElementById('taskModalTitle').textContent = '编辑监测任务';
    document.getElementById('taskQuestion').value = task.question;
    document.getElementById('taskBrands').value = task.brands.join('; ');
    document.getElementById('taskModal').style.display = 'flex';
}

function closeTaskModal() {
    document.getElementById('taskModal').style.display = 'none';
    editingTaskIdx = -1;
}

async function saveTaskModal() {
    if (!currentProjectId) return;

    const question = document.getElementById('taskQuestion').value.trim();
    const brandsStr = document.getElementById('taskBrands').value.trim();

    if (!question) {
        alert('请输入问题');
        return;
    }
    if (!brandsStr) {
        alert('请输入品牌');
        return;
    }

    const brands = brandsStr.split(';').map(b => b.trim()).filter(b => b);

    if (editingTaskIdx >= 0) {
        currentTasks[editingTaskIdx] = {question, brands};
    } else {
        currentTasks.push({question, brands});
    }

    await saveTasks();
    closeTaskModal();
}

async function deleteTask(idx) {
    if (!confirm('确定要删除这个任务吗？')) return;

    currentTasks.splice(idx, 1);
    await saveTasks();
}

async function saveTasks() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/config/tasks`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({tasks: currentTasks})
        });
        const data = await response.json();

        if (!data.success) {
            alert('保存失败: ' + data.error);
            return;
        }

        renderTaskList();
    } catch (error) {
        console.error('保存任务失败:', error);
        alert('保存任务失败');
    }
}

// ========== 执行控制 ==========

function startStatusPolling() {
    setInterval(loadStatus, 1000);
    loadStatus();
}

async function loadStatus() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/run/status`);
        const data = await response.json();

        const statusText = document.getElementById('statusText');
        const startBtn = document.getElementById('startBtn');

        if (data.is_running) {
            statusText.textContent = '状态: 运行中...';
            statusText.style.color = '#059669';
            startBtn.disabled = true;
            startBtn.style.opacity = '0.5';
        } else {
            statusText.textContent = '状态: 空闲';
            statusText.style.color = '#666';
            startBtn.disabled = false;
            startBtn.style.opacity = '1';
        }

        const logContent = document.getElementById('logContent');
        if (data.logs && data.logs.length > 0) {
            logContent.innerHTML = data.logs.map(log => `<div class="log-line">${escapeHtml(log)}</div>`).join('');
            logContent.scrollTop = logContent.scrollHeight;
        } else {
            logContent.innerHTML = '等待执行...';
        }
    } catch (error) {
        console.error('加载状态失败:', error);
    }
}

async function startMonitor() {
    if (!currentProjectId) return;

    if (!confirm('确定要开始执行监测任务吗？浏览器窗口会弹出。')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/run/start`, {
            method: 'POST'
        });
        const data = await response.json();

        if (!data.success) {
            alert('启动失败: ' + data.error);
        }
    } catch (error) {
        console.error('启动失败:', error);
        alert('启动失败');
    }
}

// ========== 定时监测 ==========

async function loadSchedule() {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/config/schedule`);
        const data = await response.json();

        if (data.success) {
            renderHourSelector(data.schedule_hours || []);
        }
    } catch (error) {
        console.error('加载定时设置失败:', error);
    }
}

function renderHourSelector(selectedHours) {
    const container = document.getElementById('hourSelector');
    container.innerHTML = '';

    for (let hour = 0; hour < 24; hour++) {
        const selected = selectedHours.includes(hour);

        const div = document.createElement('div');
        div.className = 'hour-checkbox' + (selected ? ' selected' : '');

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = 'hour-' + hour;
        checkbox.checked = selected;
        checkbox.onclick = () => toggleHour(hour);

        const label = document.createElement('label');
        label.htmlFor = 'hour-' + hour;
        label.textContent = hour + ':00';

        div.appendChild(checkbox);
        div.appendChild(label);
        div.onclick = () => toggleHour(hour);

        container.appendChild(div);
    }
}

function toggleHour(hour) {
    const checkbox = document.getElementById('hour-' + hour);
    const div = checkbox.parentElement;

    if (checkbox.checked) {
        checkbox.checked = false;
        div.classList.remove('selected');
    } else {
        checkbox.checked = true;
        div.classList.add('selected');
    }
}

async function saveSchedule() {
    if (!currentProjectId) return;

    const selectedHours = [];
    for (let hour = 0; hour < 24; hour++) {
        const checkbox = document.getElementById('hour-' + hour);
        if (checkbox && checkbox.checked) {
            selectedHours.push(hour);
        }
    }

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/config/schedule`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({schedule_hours: selectedHours})
        });
        const data = await response.json();

        if (!data.success) {
            alert('保存失败: ' + data.error);
            return;
        }

        alert('保存成功！已选择 ' + selectedHours.length + ' 个时间点');
        loadSchedulerStatus();
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败');
    }
}

async function loadSchedulerStatus() {
    try {
        const response = await fetch('/api/scheduler/status');
        const data = await response.json();

        const statusText = document.getElementById('schedulerStatusText');
        const jobsList = document.getElementById('scheduledJobsList');

        if (!data.success) {
            statusText.textContent = '❌ 加载状态失败: ' + data.error;
            return;
        }

        if (!data.available) {
            statusText.textContent = '⚠️ ' + data.message;
            jobsList.innerHTML = '请安装 APScheduler';
            return;
        }

        if (data.running) {
            statusText.textContent = '✓ 调度器运行中';
            statusText.style.color = '#059669';
        } else {
            statusText.textContent = '✗ 调度器未运行';
            statusText.style.color = '#dc2626';
        }

        if (data.jobs && data.jobs.length > 0) {
            // 按项目分组
            const grouped = {};
            data.jobs.forEach(job => {
                // 从job.name中提取项目名和时间，格式是"项目名_时间:00"
                const match = job.name.match(/^(.+)_(\d+):00$/);
                let projectName = job.name;
                let hour = '';
                if (match) {
                    projectName = match[1];
                    hour = match[2];
                }

                if (!grouped[projectName]) {
                    grouped[projectName] = {
                        hours: [],
                        next_run_time: job.next_run_time
                    };
                }
                if (hour) {
                    grouped[projectName].hours.push(parseInt(hour));
                }
                // 保留最早的下次执行时间
                if (!grouped[projectName].next_run_time ||
                    (job.next_run_time && job.next_run_time < grouped[projectName].next_run_time)) {
                    grouped[projectName].next_run_time = job.next_run_time;
                }
            });

            // 渲染分组后的任务
            let html = '';
            for (const projectName in grouped) {
                const info = grouped[projectName];
                // 对小时排序
                info.hours.sort((a, b) => a - b);
                // 生成连续时间段描述
                const timeDesc = formatTimeRange(info.hours);

                html += `
                    <div class="scheduled-job-group">
                        <div class="scheduled-job-header">
                            <span class="scheduled-job-project">${escapeHtml(projectName)}</span>
                        </div>
                        <div class="scheduled-job-times">
                            <span class="time-label">定时:</span>
                            ${timeDesc}
                        </div>
                        <div class="scheduled-job-next">
                            下次执行: ${escapeHtml(info.next_run_time || '未知')}
                        </div>
                    </div>
                `;
            }
            jobsList.innerHTML = html;
        } else {
            jobsList.innerHTML = '<span style="color: #999;">暂无定时任务，请在上方选择时间并保存</span>';
        }
    } catch (error) {
        console.error('加载调度器状态失败:', error);
    }
}

// 格式化时间范围，例如 [9,10,11,14,15] -> "9:00-11:00, 14:00-15:00"
function formatTimeRange(hours) {
    if (hours.length === 0) return '';
    if (hours.length === 1) return `<span class="time-tag">${hours[0]}:00</span>`;

    // 查找连续时间段
    const ranges = [];
    let start = hours[0];
    let end = hours[0];

    for (let i = 1; i < hours.length; i++) {
        if (hours[i] === end + 1) {
            end = hours[i];
        } else {
            ranges.push({start, end});
            start = hours[i];
            end = hours[i];
        }
    }
    ranges.push({start, end});

    // 生成描述
    return ranges.map(r => {
        if (r.start === r.end) {
            return `<span class="time-tag">${r.start}:00</span>`;
        } else {
            return `<span class="time-tag range">${r.start}:00-${r.end}:00</span>`;
        }
    }).join('');
}

// ========== 辅助函数 ==========

function formatDate(dateStr) {
    if (!dateStr) return '';
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    return `${year}-${month}-${day}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('click', (e) => {
    if (e.target.id === 'taskModal') closeTaskModal();
    if (e.target.id === 'createProjectModal') closeCreateProjectDialog();
    if (e.target.id === 'settingsModal') closeSettingsModal();
});

// ========== 全局设置弹窗 ==========

let queuePollingInterval = null;

function openSettingsModal() {
    document.getElementById('settingsModal').style.display = 'flex';
    loadSettings();
    loadQueueStatus();

    // 开始轮询队列状态
    if (queuePollingInterval) clearInterval(queuePollingInterval);
    queuePollingInterval = setInterval(loadQueueStatus, 3000);
}

function closeSettingsModal() {
    document.getElementById('settingsModal').style.display = 'none';
    if (queuePollingInterval) {
        clearInterval(queuePollingInterval);
        queuePollingInterval = null;
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/global-settings');
        const data = await response.json();

        if (data.success) {
            const s = data.settings;
            document.getElementById('settingsBrowser').value = s.browser || 'Chrome';
            document.getElementById('settingsProfile').value = s.chrome_profile || '';
            document.getElementById('settingsModel').value = s.model || '';
            document.getElementById('settingsBaseUrl').value = s.base_url || '';
            document.getElementById('settingsApiKey').value = s.api_key || '';
        }
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

async function saveSettings() {
    const statusEl = document.getElementById('settingsStatus');
    statusEl.textContent = '保存中...';
    statusEl.style.color = '#667eea';

    try {
        const response = await fetch('/api/global-settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                browser: document.getElementById('settingsBrowser').value,
                chrome_profile: document.getElementById('settingsProfile').value,
                model: document.getElementById('settingsModel').value,
                base_url: document.getElementById('settingsBaseUrl').value,
                api_key: document.getElementById('settingsApiKey').value
            })
        });
        const data = await response.json();

        if (data.success) {
            statusEl.textContent = '✓ 保存成功！';
            statusEl.style.color = '#059669';
            setTimeout(() => {
                statusEl.textContent = '';
            }, 2000);
        } else {
            statusEl.textContent = '✗ 保存失败: ' + data.error;
            statusEl.style.color = '#dc2626';
        }
    } catch (error) {
        console.error('保存设置失败:', error);
        statusEl.textContent = '✗ 保存失败';
        statusEl.style.color = '#dc2626';
    }
}

async function detectProfile() {
    const browser = document.getElementById('settingsBrowser').value;
    const statusEl = document.getElementById('settingsStatus');

    statusEl.textContent = '检测中...';
    statusEl.style.color = '#667eea';

    try {
        const response = await fetch('/api/detect-profile', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({browser})
        });
        const data = await response.json();

        if (data.success) {
            document.getElementById('settingsProfile').value = data.profile;
            if (data.browser !== browser) {
                document.getElementById('settingsBrowser').value = data.browser;
            }
            statusEl.textContent = '✓ 检测成功！';
            statusEl.style.color = '#059669';
            setTimeout(() => {
                statusEl.textContent = '';
            }, 2000);
        } else {
            statusEl.textContent = '✗ ' + data.error;
            statusEl.style.color = '#dc2626';
        }
    } catch (error) {
        console.error('检测失败:', error);
        statusEl.textContent = '✗ 检测失败';
        statusEl.style.color = '#dc2626';
    }
}

// ========== 队列状态显示 ==========

async function loadQueueStatus() {
    try {
        const response = await fetch('/api/queue/status');
        const data = await response.json();

        if (data.success) {
            // 更新队列计数
            document.getElementById('queueCount').textContent = data.current_size;

            // 更新当前执行状态
            const currentEl = document.getElementById('queueCurrent');
            if (data.current_task) {
                currentEl.innerHTML = `🔄 正在执行: <strong>${escapeHtml(data.current_task.project_name)}</strong>`;
                currentEl.style.color = '#059669';
            } else {
                currentEl.textContent = '当前空闲';
                currentEl.style.color = '#666';
            }

            // 更新队列列表
            const queueListEl = document.getElementById('queueList');
            if (data.queued_tasks && data.queued_tasks.length > 0) {
                queueListEl.style.display = 'block';
                queueListEl.innerHTML = data.queued_tasks.map((task, idx) => `
                    <div class="queue-item">
                        <span class="queue-item-num">${idx + 1}</span>
                        <span class="queue-item-name">${escapeHtml(task.project_name)}</span>
                        <span class="queue-item-time">${task.enqueue_time || ''}</span>
                    </div>
                `).join('');
            } else {
                queueListEl.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('加载队列状态失败:', error);
    }

    // 同时检查 CAPTCHA 状态
    try {
        const captchaResponse = await fetch('/api/captcha/status');
        const captchaData = await captchaResponse.json();

        if (captchaData.success) {
            const captchaAlert = document.getElementById('captchaAlert');
            const pauseBtn = document.getElementById('pauseBtn');
            const continueBtn = document.getElementById('continueBtn');

            if (captchaData.pending) {
                captchaAlert.style.display = 'block';
                pauseBtn.style.display = 'none';
                continueBtn.style.display = 'inline-block';
            } else {
                captchaAlert.style.display = 'none';
                if (captchaData.is_paused) {
                    pauseBtn.style.display = 'none';
                    continueBtn.style.display = 'inline-block';
                } else {
                    pauseBtn.style.display = 'inline-block';
                    continueBtn.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('检查CAPTCHA状态失败:', error);
    }
}

async function pauseTask() {
    try {
        const response = await fetch('/api/pause', {method: 'POST'});
        const data = await response.json();
        if (data.success) {
            document.getElementById('pauseBtn').style.display = 'none';
            document.getElementById('continueBtn').style.display = 'inline-block';
        }
    } catch (error) {
        console.error('暂停失败:', error);
    }
}

async function continueTask() {
    try {
        const response = await fetch('/api/continue', {method: 'POST'});
        const data = await response.json();
        if (data.success) {
            document.getElementById('pauseBtn').style.display = 'inline-block';
            document.getElementById('continueBtn').style.display = 'none';
            document.getElementById('captchaAlert').style.display = 'none';
        }
    } catch (error) {
        console.error('继续失败:', error);
    }
}

async function continueAfterCaptcha() {
    await continueTask();
}
