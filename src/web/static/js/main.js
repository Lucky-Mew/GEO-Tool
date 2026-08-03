// GEO 品牌监测 - 主应用逻辑

let currentProjectId = null;
let statusPollingTimer = null;
let isCurrentlyRunning = false;
let currentProjectName = '';
let trendChart = null;
let positionChart = null;
let trendStats = [];
let isProjectManagementMode = false;
let isFileManagementMode = false;
let isTaskManagementMode = false;

// GEO 关键词分页状态
let currentKeywordPage = 1;
let keywordPageSize = 5;
let keywordPaginationData = null;

// 页面加载
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    // 初始化内容类型切换
    initContentTypeToggle();
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

    if (isProjectManagementMode) {
        // 管理模式：显示带删除按钮的项目列表和添加项目卡片
        let html = '';

        if (projects && projects.length > 0) {
            html += projects.map(project => `
                <div class="project-item manage-mode" id="project-${project.id}">
                    <div class="project-info" onclick="selectProject(${project.id}, '${escapeHtml(project.name)}', '${escapeHtml(project.description)}')">
                        <div class="project-item-name">${escapeHtml(project.name)}</div>
                        ${project.description ? `<div class="project-item-desc">${escapeHtml(project.description)}</div>` : ''}
                    </div>
                    <button class="btn-delete-project" onclick="deleteProject(event, ${project.id}, '${escapeHtml(project.name)}')" title="删除项目">
                        🗑️
                    </button>
                </div>
            `).join('');
        }

        // 添加项目卡片
        html += `
            <div class="project-item add-project-card" onclick="showCreateProjectDialog()">
                <div class="add-project-icon">+</div>
                <div class="add-project-text">新建项目</div>
            </div>
        `;

        container.innerHTML = html;
    } else {
        // 普通模式：显示正常的项目列表
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

function toggleProjectManagement() {
    isProjectManagementMode = !isProjectManagementMode;
    const btn = document.getElementById('manage-projects-btn');

    if (isProjectManagementMode) {
        btn.textContent = '✓ 完成管理';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-success');
    } else {
        btn.textContent = '⚙️ 管理项目';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-primary');
    }

    // 重新加载项目列表以更新显示
    loadProjects();
}

async function deleteProject(event, projectId, projectName) {
    event.stopPropagation(); // 防止触发项目选择

    if (!confirm(`确定要删除项目 "${projectName}" 吗？\n\n此操作将删除该项目的所有数据（包括监测任务、历史记录、分析报告等），且无法恢复！`)) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            alert('项目已成功删除');

            // 如果删除的是当前选中的项目，清空选择
            if (currentProjectId === projectId) {                currentProjectId = null;
                currentProjectName = '';
                document.getElementById('noProjectSelected').style.display = 'flex';
                document.getElementById('projectContent').style.display = 'none';
            }

            // 重新加载项目列表
            loadProjects();
        } else {
            alert('删除失败: ' + data.error);
        }
    } catch (error) {
        console.error('删除项目失败:', error);
        alert('删除失败');
    }
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
            if (!isProjectManagementMode) {
                selectProject(data.project_id, name, desc);
            }
        } else {            alert('创建失败: ' + data.error);
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
    console.log('初始化图表...');

    // 确保图表容器有尺寸
    const trendDom = document.getElementById('trendChart');
    const positionDom = document.getElementById('positionChart');

    if (!trendDom || !positionDom) {
        console.error('找不到图表容器');
        return;
    }

    // 设置容器高度
    trendDom.style.height = '350px';
    trendDom.style.width = '100%';
    positionDom.style.height = '320px';
    positionDom.style.width = '100%';

    if (!trendChart) {
        trendChart = echarts.init(trendDom);
        console.log('趋势图初始化完成');
    }

    if (!positionChart) {
        positionChart = echarts.init(positionDom);
        console.log('位置图初始化完成');
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
        document.getElementById('totalMentions').textContent = totalMentionCount;

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
    const isCompact = container.classList.contains('compact');

    if (!dates || dates.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>暂无数据</p>
            </div>
        `;
        return;
    }

    if (isCompact) {
        container.innerHTML = dates.map(date => {
            const summary = summaries.find(s => s.date_str === date);
            const mentionCount = summary?.brand_mentioned_count || 0;
            const totalQ = summary?.total_questions || 0;
            const rate = totalQ > 0 ? Math.round((mentionCount / totalQ) * 100) : 0;

            return `
                <div class="date-item compact" onclick="showDetail('${date}')">
                    <span class="date-text">${formatDate(date)}</span>
                    <span class="rate-badge" style="background: ${rate >= 70 ? '#10b981' : rate >= 40 ? '#f59e0b' : '#ef4444'}">${rate}%</span>
                </div>
            `;
        }).join('');
    } else {
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
}

function renderTrendChart(stats) {
    console.log('渲染趋势图，数据:', stats);
    if (!trendChart) {
        console.error('趋势图未初始化');
        return;
    }
    trendStats = stats;

    if (!stats || stats.length === 0) {
        console.log('没有数据，显示空图表');
        const option = {
            title: {
                text: '暂无数据',
                left: 'center',
                top: 'center',
                textStyle: {color: '#999', fontSize: 16}
            }
        };
        trendChart.setOption(option, true);
        return;
    }

    const dates = stats.map(s => formatDate(s.date_str));
    const mentionRates = stats.map(s => {
        const q = s.question_count || 0;
        const m = s.mention_count || 0;
        return q > 0 ? Math.round((m / q) * 100) : 0;
    });
    const mentionCounts = stats.map(s => s.mention_count || 0);

    console.log('日期:', dates);
    console.log('提及率:', mentionRates);
    console.log('提及次数:', mentionCounts);

    const option = {
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: ['提及率', '提及次数'],
            top: 0
        },
        grid: {left: '5%', right: '8%', bottom: '18%', top: '15%', containLabel: true},
        xAxis: {
            type: 'category',
            boundaryGap: true,
            data: dates
        },
        yAxis: [
            {
                type: 'value',
                name: '提及率',
                min: 0,
                max: 100,
                position: 'left',
                axisLabel: {formatter: '{value}%'},
                nameGap: 30
            },
            {
                type: 'value',
                name: '提及次数',
                position: 'right',
                splitLine: {show: false},
                nameGap: 30
            }
        ],
        dataZoom: [
            {
                type: 'slider',
                show: true,
                xAxisIndex: [0],
                start: 0,
                end: 100,
                bottom: 30,
                height: 20,
                handleSize: '80%',
                handleStyle: {
                    color: '#667eea',
                    borderColor: '#667eea'
                },
                fillerStyle: {
                    color: 'rgba(102, 126, 234, 0.2)'
                },
                backgroundColor: '#f0f0f0',
                showDetail: false
            },
            {
                type: 'inside',
                xAxisIndex: [0],
                start: 0,
                end: 100
            }
        ],
        series: [
            {
                name: '提及率',
                type: 'line',
                smooth: true,
                yAxisIndex: 0,
                data: mentionRates,
                symbol: 'circle',
                symbolSize: 8,
                showSymbol: true,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {offset: 0, color: 'rgba(102, 126, 234, 0.3)'},
                        {offset: 1, color: 'rgba(102, 126, 234, 0.05)'}
                    ])
                },
                lineStyle: {color: '#667eea', width: 2},
                itemStyle: {
                    color: '#667eea'
                },
                label: {
                    show: true,
                    position: 'top',
                    color: '#667eea',
                    formatter: '{c}%'
                }
            },
            {
                name: '提及次数',
                type: 'bar',
                yAxisIndex: 1,
                data: mentionCounts,
                barWidth: '20%',
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {offset: 0, color: 'rgba(245, 158, 11, 0.9)'},
                        {offset: 1, color: 'rgba(245, 158, 11, 0.5)'}
                    ]),
                    borderRadius: [4, 4, 0, 0]
                }
            }
        ]
    };

    trendChart.setOption(option, true);
    console.log('趋势图渲染完成');
}

function renderPositionChart(positionData, brandName) {
    console.log('渲染位置图，数据:', positionData);
    if (!positionChart) {
        console.error('位置图未初始化');
        return;
    }

    const positionLabels = {'first': '开头', 'middle': '中间', 'last': '结尾'};
    const colorList = ['#667eea', '#f59e0b', '#10b981'];
    const categories = [];
    const values = [];
    let total = 0;

    for (const pos in positionData) {
        categories.push(positionLabels[pos] || pos);
        values.push(positionData[pos]);
        total += positionData[pos];
    }

    console.log('位置:', categories);
    console.log('数值:', values);
    console.log('总计:', total);

    if (categories.length === 0 || total === 0) {
        console.log('没有位置数据');
        const option = {
            title: {
                text: '暂无数据',
                left: 'center',
                top: 'center',
                textStyle: {color: '#999', fontSize: 16}
            }
        };
        positionChart.setOption(option, true);
        return;
    }

    const option = {
        tooltip: {
            trigger: 'item',
            confine: true,
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: '#e5e7eb',
            borderWidth: 1,
            textStyle: {color: '#374151'},
            formatter: '{b}<br/>{c}次 ({d}%)'
        },
        legend: {
            orient: 'horizontal',
            bottom: '5%',
            left: 'center',
            itemWidth: 12,
            itemHeight: 12,
            textStyle: {color: '#4b5563', fontSize: 13},
            itemGap: 20
        },
        graphic: [
            {
                type: 'text',
                left: 'center',
                top: '42%',
                style: {
                    text: total + '',
                    textAlign: 'center',
                    fill: '#1f2937',
                    fontSize: 28,
                    fontWeight: 'bold'
                }
            },
            {
                type: 'text',
                left: 'center',
                top: '55%',
                style: {
                    text: '总提及',
                    textAlign: 'center',
                    fill: '#9ca3af',
                    fontSize: 13
                }
            }
        ],
        series: [{
            name: '出现次数',
            type: 'pie',
            radius: ['35%', '55%'],
            center: ['50%', '45%'],
            avoidLabelOverlap: true,
            itemStyle: {
                borderRadius: 8,
                borderColor: '#fff',
                borderWidth: 3
            },
            label: {
                show: false
            },
            labelLine: {
                show: false
            },
            emphasis: {
                scale: true,
                scaleSize: 8,
                itemStyle: {
                    shadowBlur: 10,
                    shadowColor: 'rgba(0,0,0,0.2)'
                }
            },
            data: categories.map((cat, i) => ({
                value: values[i],
                name: cat,
                itemStyle: {color: colorList[i % colorList.length]}
            }))
        }]
    };

    positionChart.setOption(option, true);
    console.log('位置图渲染完成');
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

        if (isFileManagementMode) {
            // 管理模式：显示带删除按钮的列表
            container.innerHTML = dates.map(date => `
                <div class="date-item" style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px;">
                    <div onclick="showTaskList('${date}')" style="flex:1;cursor:pointer;">
                        <div class="date-item-title">${formatDate(date)}</div>
                    </div>
                    <button class="btn-delete-project" onclick="deleteDate(event, '${date}')" title="删除此日期">
                        🗑️
                    </button>
                </div>
            `).join('');
        } else {
            // 普通模式：只显示日期
            container.innerHTML = dates.map(date => `
                <div class="date-item" onclick="showTaskList('${date}')">
                    <div class="date-item-title">${formatDate(date)}</div>
                </div>
            `).join('');
        }
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

        if (isTaskManagementMode) {
            container.innerHTML = data.tasks.map(task => `
                <div class="task-item" style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                    <div onclick="showTaskDetail('${task.folder}')" style="cursor:pointer;flex:1;">
                        <div class="task-item-title">${escapeHtml(task.folder)}</div>
                        <div class="task-item-question">${escapeHtml(task.question)}</div>
                    </div>
                    <button class="btn-delete-project" onclick="deleteTask(event, '${task.folder}')" title="删除此任务">
                        🗑️
                    </button>
                </div>
            `).join('');
        } else {
            container.innerHTML = data.tasks.map(task => `
                <div class="task-item" onclick="showTaskDetail('${task.folder}')">
                    <div class="task-item-title">${escapeHtml(task.folder)}</div>
                    <div class="task-item-question">${escapeHtml(task.question)}</div>
                </div>
            `).join('');
        }

        document.getElementById('taskSection').scrollIntoView({behavior: 'smooth'});
    } catch (error) {
        console.error('加载任务列表失败:', error);
    }
}

function toggleTaskManagement() {
    isTaskManagementMode = !isTaskManagementMode;
    const btn = document.getElementById('manage-tasks-btn');

    if (isTaskManagementMode) {
        btn.textContent = '✓ 完成管理';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-success');
    } else {
        btn.textContent = '⚙️ 管理删除';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-secondary');
    }

    // 重新加载列表
    if (currentDate) {
        showTaskList(currentDate);
    }
}

function toggleFileManagement() {
    isFileManagementMode = !isFileManagementMode;
    const btn = document.getElementById('manage-files-btn');

    if (isFileManagementMode) {
        btn.textContent = '✓ 完成管理';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-success');
    } else {
        btn.textContent = '⚙️ 管理删除';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-primary');
    }

    // 重新加载列表
    loadFileDateList();
}

function backToDateList() {
    document.getElementById('taskSection').style.display = 'none';
    document.getElementById('taskDetailSection').style.display = 'none';
    // 重置任务管理模式
    isTaskManagementMode = false;
    const btn = document.getElementById('manage-tasks-btn');
    if (btn) {
        btn.textContent = '⚙️ 管理删除';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-secondary');
    }
}

async function deleteDate(event, dateStr) {
    if (event) event.stopPropagation();
    if (!currentProjectId) return;
    if (!confirm(`确定要删除 ${formatDate(dateStr)} 的所有数据吗？这会同时删除文件和数据库记录！`)) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/date/${dateStr}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            alert('删除成功！');
            loadFileDateList();
            backToDateList();
            // 刷新仪表盘数据
            if (typeof loadDashboardData === 'function') {
                loadDashboardData();
            } else if (typeof initDashboardView === 'function') {
                initDashboardView();
            }
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

async function deleteTask(event, taskFolder) {
    if (event) event.stopPropagation();
    if (!currentProjectId || !currentDate) return;
    if (!confirm(`确定要删除任务 "${taskFolder}" 吗？`)) return;

    try {
        const response = await fetch(`/api/projects/${currentProjectId}/date/${currentDate}/task/${encodeURIComponent(taskFolder)}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            alert('删除成功！');
            showTaskList(currentDate); // 刷新列表
            backToTaskList();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
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
    loadStatus();
    scheduleNextPoll(3000); // 初始3秒刷新一次
}

function scheduleNextPoll(delay) {
    if (statusPollingTimer) {
        clearTimeout(statusPollingTimer);
    }
    statusPollingTimer = setTimeout(() => {
        loadStatus();
    }, delay);
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
            isCurrentlyRunning = true;
        } else {
            statusText.textContent = '状态: 空闲';
            statusText.style.color = '#666';
            startBtn.disabled = false;
            startBtn.style.opacity = '1';
            isCurrentlyRunning = false;
        }

        const logContent = document.getElementById('logContent');
        if (data.logs && data.logs.length > 0) {
            logContent.innerHTML = data.logs.map(log => `<div class="log-line">${escapeHtml(log)}</div>`).join('');
            logContent.scrollTop = logContent.scrollHeight;
        } else {
            logContent.innerHTML = '等待执行...';
        }

        // 根据状态决定下一次刷新的间隔
        const nextDelay = isCurrentlyRunning ? 1000 : 5000; // 运行时1秒，空闲时5秒
        scheduleNextPoll(nextDelay);
    } catch (error) {
        console.error('加载状态失败:', error);
        scheduleNextPoll(5000); // 出错时5秒后重试
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

// ========== GEO 优化功能 ==========

let currentGeoView = 'documents';
let currentKeywordFilter = 'all';
let currentDocFilter = 'all';
let geoTierChart = null;
let geoPositionChart = null;

// 扩展 showView 支持 GEO 视图
const originalShowView = showView;
showView = function(viewName) {
    // 调用原始函数
    if (viewName !== 'geo') {
        document.querySelectorAll('.geo-nav-btn').forEach(b => b.classList.remove('active'));
    }

    if (viewName === 'geo') {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('geoView').classList.add('active');
        const navBtn = document.querySelector(`.nav-btn.geo-btn`);
        if (navBtn) navBtn.classList.add('active');
        initGeoView();
    } else {
        originalShowView(viewName);
    }
};

function initGeoView() {
    // 初始化 GEO 视图
    showGeoView('documents');
    loadDocuments();
}

function showGeoView(viewName) {
    currentGeoView = viewName;
    document.querySelectorAll('.geo-subview').forEach(v => v.style.display = 'none');
    document.querySelectorAll('.geo-nav-btn').forEach(b => b.classList.remove('active'));

    const viewElementId = 'geo' + viewName.charAt(0).toUpperCase() + viewName.slice(1) + 'View';
    const viewEl = document.getElementById(viewElementId);
    if (viewEl) viewEl.style.display = 'block';

    const navBtn = document.querySelector(`.geo-nav-btn[onclick="showGeoView('${viewName}')"]`);
    if (navBtn) navBtn.classList.add('active');

    if (viewName === 'keywords') {
        loadKeywordStats();
        loadKeywords();
    } else if (viewName === 'documents') {
        loadDocuments();
    } else if (viewName === 'content') {
        // 自动填充品牌名
        if (currentProjectId && currentProjectName) {
            document.getElementById('geoContentBrand').value = currentProjectName;
        }
    } else if (viewName === 'competitors') {
        loadDoubaoCitations();
    }
}

// ========== 关键词库 ==========

function filterKeywords(filter) {
    currentKeywordFilter = filter;
    document.querySelectorAll('.geo-tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    loadKeywords();
}

async function loadKeywordStats() {
    if (!currentProjectId) return;
    try {
        const response = await fetch(`/api/geo/keywords?project_id=${currentProjectId}&page=1&page_size=1000`);
        const data = await response.json();
        if (data.success && data.stats) {
            const statsContainer = document.getElementById('geoKeywordStats');
            if (statsContainer) {
                const tierNames = {brand: '品牌词', accurate: '精准词', generic: '大词', scene: '场景词'};
                let html = '<div class="stats-grid" style="grid-template-columns: repeat(4,1fr)">';
                for (const tier in data.stats) {
                    const s = data.stats[tier];
                    const color = tier === 'brand' ? '#dbeafe' : tier === 'accurate' ? '#dcfce7' : tier === 'generic' ? '#fef3c7' : '#f3e8ff';
                    const textColor = tier === 'brand' ? '#1d4ed8' : tier === 'accurate' ? '#15803d' : tier === 'generic' ? '#b45309' : '#7e22ce';
                    html += `
                        <div class="stat-card" style="background: ${color}">
                            <div class="stat-value" style="color: ${textColor}; font-size:1.8em">${s.total}</div>
                            <div class="stat-label" style="color: ${textColor}">${tierNames[tier]}</div>
                        </div>
                    `;
                }
                html += '</div>';
                statsContainer.innerHTML = html;
            }
        }
    } catch (error) {
        console.error('加载关键词统计失败:', error);
    }
}

async function loadKeywords(resetPage = true) {
    if (!currentProjectId) return;
    if (resetPage) {
        currentKeywordPage = 1;
    }

    const container = document.getElementById('geoKeywordList');
    if (container) {
        container.innerHTML = '<div style="padding:20px;text-align:center;">加载中...</div>';
    }

    try {
        let url = `/api/geo/keywords?project_id=${currentProjectId}&page=${currentKeywordPage}&page_size=${keywordPageSize}`;
        if (currentKeywordFilter !== 'all') {
            url += `&tier=${currentKeywordFilter}`;
        }
        const response = await fetch(url);
        const data = await response.json();
        if (data.success) {
            keywordPaginationData = data.pagination;
            renderKeywords(data.keywords);
            try {
                renderKeywordPagination();
            } catch (e) {
                console.error('分页渲染失败:', e);
            }
        }
    } catch (error) {
        console.error('加载关键词失败:', error);
        if (container) {
            container.innerHTML = '<div style="padding:20px;text-align:center;color:red;">加载失败</div>';
        }
    }
}

function renderKeywordPagination() {
    const container = document.getElementById('geoKeywordPagination');
    if (!container || !keywordPaginationData) return;

    const {page, page_size, total, total_pages} = keywordPaginationData;

    if (total === 0) {
        container.innerHTML = '';
        return;
    }

    let html = '<div class="pagination-container">';

    // 每页条数选择
    html += `
        <div class="page-size-selector">
            每页:
            <select onchange="changePageSize(this.value)" style="margin-left: 8px; padding: 4px 8px; border-radius: 4px; border: 1px solid #d1d5db">
                <option value="5" ${keywordPageSize === 5 ? 'selected' : ''}>5条</option>
                <option value="10" ${keywordPageSize === 10 ? 'selected' : ''}>10条</option>
            </select>
        </div>
    `;

    // 分页信息
    const start = (page - 1) * page_size + 1;
    const end = Math.min(page * page_size, total);
    html += `<div class="pagination-info">显示 ${start}-${end} 条，共 ${total} 条</div>`;

    // 分页按钮
    html += '<div class="pagination-buttons">';
    html += `<button class="pagination-btn" onclick="goToPage(1)" ${page === 1 ? 'disabled' : ''}>首页</button>`;
    html += `<button class="pagination-btn" onclick="goToPage(${page - 1})" ${page === 1 ? 'disabled' : ''}>上一页</button>`;
    html += `<span class="pagination-current">第 ${page} / ${total_pages} 页</span>`;
    html += `<button class="pagination-btn" onclick="goToPage(${page + 1})" ${page === total_pages ? 'disabled' : ''}>下一页</button>`;
    html += `<button class="pagination-btn" onclick="goToPage(${total_pages})" ${page === total_pages ? 'disabled' : ''}>末页</button>`;
    html += '</div>';

    html += '</div>';
    container.innerHTML = html;
}

function goToPage(page) {
    if (!keywordPaginationData) return;
    if (page < 1 || page > keywordPaginationData.total_pages) return;
    currentKeywordPage = page;
    loadKeywords(false);
}

function changePageSize(size) {
    keywordPageSize = parseInt(size);
    currentKeywordPage = 1;
    loadKeywords(false);
}

function renderKeywords(keywords) {
    const container = document.getElementById('geoKeywordList');
    if (!keywords || keywords.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="background:white; border:2px dashed #e5e7eb; border-radius:8px">
                <div class="empty-state-icon" style="color:#9ca3af">📭</div>
                <p style="color:#4b5563; font-weight:500">暂无关键词</p>
                <p style="color:#6b7280">点击"自动生成"来批量创建关键词</p>
            </div>
        `;
        return;
    }

    const tierBadges = {
        brand: 'badge-brand', accurate: 'badge-accurate', generic: 'badge-generic', scene: 'badge-scene'
    };
    const tierNames = {
        brand: '品牌词', accurate: '精准词', generic: '大词', scene: '场景词'
    };

    container.innerHTML = keywords.map(kw => `
        <div class="geo-list-item">
            <div class="geo-list-header">
                <span class="geo-list-title">${escapeHtml(kw.keyword)}</span>
                <span class="geo-list-badge ${tierBadges[kw.tier]}">${tierNames[kw.tier]}</span>
            </div>
            <div class="geo-list-meta">
                难度: ${kw.difficulty}/100 ${kw.is_target ? '| ⭐ 核心词' : ''}
            </div>
            <div class="geo-list-actions">
                <button class="btn-edit" onclick="editKeyword(${kw.id})">✏️ 编辑</button>
                <button class="btn-delete" onclick="deleteKeyword(${kw.id})">🗑️ 删除</button>
            </div>
        </div>
    `).join('');
}

function openAddKeywordModal() {
    document.getElementById('newKeywordText').value = '';
    document.getElementById('newKeywordTier').value = 'brand';
    document.getElementById('newKeywordDifficulty').value = '50';
    document.getElementById('newKeywordIsTarget').checked = false;
    document.getElementById('addKeywordModal').style.display = 'flex';
}

function closeAddKeywordModal() {
    document.getElementById('addKeywordModal').style.display = 'none';
}

async function saveKeyword() {
    if (!currentProjectId) return;
    const keyword = document.getElementById('newKeywordText').value.trim();
    const tier = document.getElementById('newKeywordTier').value;
    const difficulty = parseInt(document.getElementById('newKeywordDifficulty').value);
    const isTarget = document.getElementById('newKeywordIsTarget').checked;

    if (!keyword) {
        alert('请输入关键词');
        return;
    }

    try {
        const response = await fetch('/api/geo/keywords', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: currentProjectId,
                keyword, tier, difficulty, is_target: isTarget
            })
        });
        const data = await response.json();
        if (data.success) {
            closeAddKeywordModal();
            loadKeywordStats();
            loadKeywords();
        } else {
            alert('保存失败: ' + data.error);
        }
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败');
    }
}

// GEO关键词生成状态
let generatedSuggestions = null;

async function openKeywordGenModal() {
    // 重置状态
    generatedSuggestions = null;

    // 初始化UI
    document.getElementById('genResultPreview').style.display = 'none';
    document.getElementById('genResultContent').innerHTML = '';
    document.getElementById('smartGenStatus').innerHTML = '<p style="color: #666;">点击"开始挖掘"来分析文档内容</p>';

    // 检查文档库
    const hasDocs = await checkDocumentsAndShowAlert();

    // 控制按钮状态
    const genBtn = document.getElementById('genBtnSmart');
    if (hasDocs) {
        genBtn.style.display = 'inline-block';
    } else {
        genBtn.style.display = 'none';
    }

    document.getElementById('keywordGenModal').style.display = 'flex';
}

async function checkDocumentsAndShowAlert() {
    try {
        const response = await fetch(`/api/geo/keywords/check-docs?project_id=${currentProjectId}`);
        const data = await response.json();
        const alertEl = document.getElementById('docEmptyAlert');
        const genView = document.getElementById('genSmartView');

        if (data.success && !data.has_documents) {
            alertEl.style.display = 'block';
            genView.style.display = 'none';
            return false;
        } else {
            alertEl.style.display = 'none';
            genView.style.display = 'block';
            return true;
        }
    } catch (error) {
        console.error('检查文档失败:', error);
        return false;
    }
}

function closeKeywordGenModal() {
    document.getElementById('keywordGenModal').style.display = 'none';
    generatedSuggestions = null;
}

async function generateKeywords() {
    if (!currentProjectId) return;
    await generateKeywordsFromDocs();
}

async function generateKeywordsFromDocs() {
    const statusEl = document.getElementById('smartGenStatus');
    statusEl.innerHTML = '<p style="color: #666;">🔄 正在分析文档内容...</p>';

    try {
        const response = await fetch('/api/geo/keywords/generate-from-docs', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: currentProjectId
            })
        });
        const data = await response.json();

        if (data.success) {
            generatedSuggestions = data.suggestions;
            const total = (generatedSuggestions.brand?.length || 0) +
                         (generatedSuggestions.accurate?.length || 0) +
                         (generatedSuggestions.generic?.length || 0) +
                         (generatedSuggestions.scene?.length || 0);

            if (total === 0) {
                statusEl.innerHTML = '<p style="color: #dc2626;">未能从文档中提取到关键词，请尝试上传更多文档</p>';
                return;
            }

            // 显示预览
            renderKeywordPreview(generatedSuggestions);
            statusEl.innerHTML = `<p style="color: #16a34a;">✅ 已挖掘 ${total} 个关键词</p>`;
        } else {
            statusEl.innerHTML = `<p style="color: #dc2626;">❌ ${data.error || '生成失败'}</p>`;
        }
    } catch (error) {
        console.error('智能挖掘失败:', error);
        statusEl.innerHTML = '<p style="color: #dc2626;">❌ 生成失败</p>';
    }
}

function renderKeywordPreview(suggestions) {
    const tierNames = {brand: '品牌词', accurate: '精准词', generic: '大词', scene: '场景词'};
    const tierColors = {
        brand: '#dbeafe',
        accurate: '#dcfce7',
        generic: '#fef3c7',
        scene: '#f3e8ff'
    };
    const tierTextColors = {
        brand: '#1d4ed8',
        accurate: '#15803d',
        generic: '#b45309',
        scene: '#7e22ce'
    };

    let html = '';

    for (const tier in suggestions) {
        const keywords = suggestions[tier];
        if (!keywords || keywords.length === 0) continue;

        html += `
            <div style="margin-bottom: 16px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-weight: bold; color: ${tierTextColors[tier]};">
                        ${tierNames[tier]} (${keywords.length})
                    </span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${keywords.map(kw => `
                        <span style="padding: 4px 10px; background: ${tierColors[tier]}; border-radius: 16px; font-size: 0.9em; color: ${tierTextColors[tier]};">
                            ${escapeHtml(kw)}
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    }

    const total = (suggestions.brand?.length || 0) +
                 (suggestions.accurate?.length || 0) +
                 (suggestions.generic?.length || 0) +
                 (suggestions.scene?.length || 0);

    html += `
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e5e7eb;">
            <button class="btn-save" onclick="saveGeneratedKeywords()">
                💾 保存全部 ${total} 个关键词
            </button>
        </div>
    `;

    document.getElementById('genResultContent').innerHTML = html;
    document.getElementById('genResultPreview').style.display = 'block';
}

async function saveGeneratedKeywords() {
    if (!generatedSuggestions) {
        alert('没有可保存的关键词');
        return;
    }

    const total = (generatedSuggestions.brand?.length || 0) +
                 (generatedSuggestions.accurate?.length || 0) +
                 (generatedSuggestions.generic?.length || 0) +
                 (generatedSuggestions.scene?.length || 0);

    if (!confirm(`确定保存 ${total} 个关键词吗？`)) {
        return;
    }

    try {
        const allKeywords = [];
        for (const tier in generatedSuggestions) {
            for (const keyword of generatedSuggestions[tier]) {
                allKeywords.push({
                    keyword,
                    tier,
                    difficulty: tier === 'brand' ? 30 : tier === 'accurate' ? 50 : tier === 'generic' ? 80 : 35,
                    is_target: tier !== 'scene'
                });
            }
        }

        await fetch('/api/geo/keywords/batch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: currentProjectId,
                keywords: allKeywords
            })
        });

        closeKeywordGenModal();
        loadKeywordStats();
        loadKeywords();
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败');
    }
}

let editingKeywordId = -1;

function editKeyword(id) {
    editingKeywordId = id;
    alert('编辑功能待完善');
}

async function deleteKeyword(id) {
    if (!confirm('确定要删除这个关键词吗？')) return;
    try {
        const response = await fetch(`/api/geo/keywords/${id}`, {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();
        if (data.success) {
            loadKeywordStats();
            loadKeywords();
        }
    } catch (error) {
        console.error('删除失败:', error);
    }
}

// ========== 文档库 ==========

function filterDocuments(filter) {
    currentDocFilter = filter;
    document.querySelectorAll('#geoDocumentsView .geo-tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    loadDocuments();
}

async function loadDocuments() {
    if (!currentProjectId) return;
    try {
        let url = `/api/geo/documents?project_id=${currentProjectId}`;
        if (currentDocFilter !== 'all') {
            url += `&tag=${encodeURIComponent(currentDocFilter)}`;
        }
        const response = await fetch(url);
        const data = await response.json();
        if (data.success) {
            renderDocuments(data.documents);
            renderSummaries(data.summaries);

            // 动态生成标签过滤栏
            const tagBar = document.getElementById('geoDocumentTagBar');
            if (tagBar && data.documents) {
                const allTags = new Set();
                data.documents.forEach(doc => {
                    if (doc.tags) {
                        doc.tags.split(',').forEach(t => {
                            const tag = t.trim();
                            if (tag) allTags.add(tag);
                        });
                    }
                });

                let tagHtml = `<button class="geo-tab ${currentDocFilter === 'all' ? 'active' : ''}" onclick="filterDocuments('all')">全部</button>`;
                allTags.forEach(tag => {
                    tagHtml += `<button class="geo-tab ${currentDocFilter === tag ? 'active' : ''}" onclick="filterDocuments('${escapeHtml(tag)}')">${escapeHtml(tag)}</button>`;
                });
                tagBar.innerHTML = tagHtml;
            }
        }
    } catch (error) {
        console.error('加载文档失败:', error);
    }
}

function renderDocuments(documents) {
    const container = document.getElementById('geoDocumentList');
    if (!documents || documents.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="background:white; border:2px dashed #e5e7eb; border-radius:8px">
                <div class="empty-state-icon" style="color:#9ca3af">📄</div>
                <p style="color:#4b5563; font-weight:500">暂无文档</p>
                <p style="color:#6b7280">点击"上传文档"添加</p>
            </div>
        `;
        return;
    }

    const typeIcons = {
        text: '📝',
        markdown: '📝',
        word: '📘',
        pdf: '📕',
        powerpoint: '📊'
    };

    container.innerHTML = documents.map(doc => {
        const tags = doc.tags ? doc.tags.split(',').map(t => t.trim()).filter(t => t) : [];
        const tagBadges = tags.map(tag => `<span class="geo-list-badge" style="background:#f0f9ff; color:#0369a1">${escapeHtml(tag)}</span>`).join('');

        return `
            <div class="geo-list-item">
                <div class="geo-list-header">
                    <span class="geo-list-title">
                        ${typeIcons[doc.file_type] || '📄'} ${escapeHtml(doc.original_filename)}
                    </span>
                    ${tagBadges}
                </div>
                <div class="geo-list-meta">
                    ${doc.word_count || 0} 字 · ${formatFileSize(doc.file_size)} · ${doc.is_parsed ? '✅ 已解析' : '⏳ 待解析'}
                </div>
                ${doc.content_preview ? `<div style="margin:8px 0; color:#666; font-size:0.9em">${escapeHtml(doc.content_preview)}</div>` : ''}
                <div class="geo-list-actions">
                    <button class="btn-edit" onclick="openViewDocumentModal(${doc.id}, '${escapeHtml(doc.original_filename)}')">👁️ 查看</button>
                    <button class="btn-delete" onclick="deleteDocument(${doc.id})">🗑️ 删除</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderSummaries(summaries) {
    const container = document.getElementById('geoSummaryList');
    if (!summaries || summaries.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="background:white; border:2px dashed #e5e7eb; border-radius:8px">
                <div class="empty-state-icon" style="color:#9ca3af">📝</div>
                <p style="color:#4b5563; font-weight:500">暂无摘要</p>
                <p style="color:#6b7280">点击"创建摘要"添加</p>
            </div>
        `;
        return;
    }

    const levelNames = {
        document: '文档摘要',
        category: '分类摘要',
        global: '全局摘要'
    };

    container.innerHTML = summaries.map(s => `
        <div class="geo-list-item">
            <div class="geo-list-header">
                <span class="geo-list-title">${escapeHtml(s.title || levelNames[s.summary_level] || '摘要')}</span>
                <span class="badge badge-accurate">${levelNames[s.summary_level] || s.summary_level}</span>
            </div>
            <div class="geo-list-meta">
                ${s.is_manual_edit ? '✏️ 人工编辑' : '🤖 AI生成'}
            </div>
            <div style="margin:8px 0; color:#333">${escapeHtml(s.content)}</div>
            <div class="geo-list-actions">
                <button class="btn-edit" onclick="editSummary(${s.id}, '${escapeHtml(s.content).replace(/'/g, "\\'")}')">✏️ 编辑</button>
                <button class="btn-delete" onclick="deleteSummary(${s.id})">🗑️ 删除</button>
            </div>
        </div>
    `).join('');
}

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function openUploadDocumentModal() {
    document.getElementById('documentFile').value = '';
    document.getElementById('newDocTags').value = '';
    document.getElementById('uploadDocumentModal').style.display = 'flex';
}

function closeUploadDocumentModal() {
    document.getElementById('uploadDocumentModal').style.display = 'none';
}

async function uploadDocument() {
    if (!currentProjectId) return;
    const fileInput = document.getElementById('documentFile');
    const file = fileInput.files[0];
    if (!file) {
        alert('请选择文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', currentProjectId);
    formData.append('tags', document.getElementById('newDocTags').value);

    try {
        const response = await fetch('/api/geo/documents', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            closeUploadDocumentModal();
            alert('上传成功！解析了 ' + data.word_count + ' 字，切分为 ' + data.chunks + ' 个片段');
            loadDocuments();
        } else {
            alert('上传失败: ' + data.error);
        }
    } catch (error) {
        console.error('上传失败:', error);
        alert('上传失败');
    }
}

function openViewDocumentModal(docId, filename) {
    document.getElementById('viewDocTitle').textContent = '📄 ' + filename;
    document.getElementById('viewDocContent').textContent = '加载中...';
    document.getElementById('viewDocumentModal').style.display = 'flex';
    viewDocument(docId);
}

function closeViewDocumentModal() {
    document.getElementById('viewDocumentModal').style.display = 'none';
}

async function viewDocument(docId) {
    try {
        const response = await fetch(`/api/geo/documents/${docId}`);
        const data = await response.json();
        if (data.success) {
            let content = data.full_content || '无法读取完整内容';
            document.getElementById('viewDocContent').textContent = content;
        }
    } catch (error) {
        console.error('查看失败:', error);
        document.getElementById('viewDocContent').textContent = '加载失败';
    }
}

async function deleteDocument(docId) {
    if (!confirm('确定要删除这个文档吗？')) return;
    try {
        const response = await fetch(`/api/geo/documents/${docId}`, {method: 'DELETE'});
        const data = await response.json();
        if (data.success) {
            loadDocuments();
        }
    } catch (error) {
        console.error('删除失败:', error);
    }
}

let currentSummaryMode = 'document';
let currentDocumentsForSummary = [];

function openCreateSummaryModal(level) {
    currentSummaryMode = level || 'document';
    document.getElementById('summaryLevel').value = level || 'document';
    document.getElementById('summaryTitle').value = '';
    document.getElementById('summaryContent').value = '';
    updateSummaryTarget();
    document.getElementById('createSummaryModal').style.display = 'flex';
}

function closeCreateSummaryModal() {
    document.getElementById('createSummaryModal').style.display = 'none';
}

async function updateSummaryTarget() {
    const level = document.getElementById('summaryLevel').value;
    const targetGroup = document.getElementById('summaryTargetGroup');

    if (level === 'document' && currentProjectId) {
        targetGroup.style.display = 'block';
        const select = document.getElementById('summaryTargetId');
        try {
            const response = await fetch(`/api/geo/documents?project_id=${currentProjectId}`);
            const data = await response.json();
            if (data.success) {
                currentDocumentsForSummary = data.documents;
                select.innerHTML = data.documents.map(d =>
                    `<option value="${d.id}">${escapeHtml(d.original_filename)}</option>`
                ).join('');
            }
        } catch (error) {
            console.error('加载文档列表失败:', error);
        }
    } else if (level === 'category') {
        targetGroup.style.display = 'block';
        const select = document.getElementById('summaryTargetId');
        select.innerHTML = `
            <option value="price">价格数据</option>
            <option value="period">周期数据</option>
            <option value="technical">技术参数</option>
            <option value="patent">专利信息</option>
            <option value="clinical">临床背书</option>
            <option value="population">适用人群</option>
        `;
    } else {
        targetGroup.style.display = 'none';
    }
}

async function generateSummary() {
    const level = document.getElementById('summaryLevel').value;
    if (level !== 'document') {
        alert('目前仅支持为单个文档自动生成摘要');
        return;
    }
    const docId = document.getElementById('summaryTargetId').value;
    if (!docId) {
        alert('请先选择一个文档');
        return;
    }

    try {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '生成中...';
        btn.disabled = true;

        const response = await fetch(`/api/geo/documents/${docId}/generate-summary`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('summaryTitle').value = data.title;
            document.getElementById('summaryContent').value = data.content;
        } else {
            alert('生成摘要失败: ' + data.error);
        }

        btn.textContent = originalText;
        btn.disabled = false;
    } catch (error) {
        console.error('生成摘要失败:', error);
        alert('生成摘要失败');
    }
}

async function saveSummary() {
    if (!currentProjectId) return;
    const level = document.getElementById('summaryLevel').value;
    const title = document.getElementById('summaryTitle').value.trim();
    const content = document.getElementById('summaryContent').value.trim();

    if (!content) {
        alert('请填写摘要内容');
        return;
    }

    let targetId = null;
    if (level === 'document') {
        targetId = parseInt(document.getElementById('summaryTargetId').value);
    } else if (level === 'category') {
        targetId = document.getElementById('summaryTargetId').value;
    }

    try {
        const response = await fetch('/api/geo/summaries', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: currentProjectId,
                summary_level: level,
                target_id: targetId,
                title,
                content,
                is_manual: true
            })
        });
        const data = await response.json();
        if (data.success) {
            closeCreateSummaryModal();
            loadDocuments();
        } else {
            alert('保存失败: ' + data.error);
        }
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败');
    }
}

function editSummary(summaryId, content) {
    const newContent = prompt('编辑摘要内容:', content);
    if (newContent !== null && newContent.trim()) {
        updateSummary(summaryId, newContent.trim());
    }
}

async function updateSummary(summaryId, content) {
    try {
        const response = await fetch(`/api/geo/summaries/${summaryId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content, is_manual: true})
        });
        const data = await response.json();
        if (data.success) {
            loadDocuments();
        }
    } catch (error) {
        console.error('更新失败:', error);
    }
}

async function deleteSummary(summaryId) {
    if (!confirm('确定要删除这个摘要吗？')) return;
    try {
        const response = await fetch(`/api/geo/summaries/${summaryId}`, {method: 'DELETE'});
        const data = await response.json();
        if (data.success) {
            loadDocuments();
        }
    } catch (error) {
        console.error('删除失败:', error);
    }
}

// ========== 内容生产助手 ==========

let allKeywordsForSelector = [];
let currentKeywordTierFilter = 'all';

// 内容类型切换时显示/隐藏对比品牌区域
function initContentTypeToggle() {
    const contentTypeSelect = document.getElementById('geoContentType');
    if (contentTypeSelect) {
        contentTypeSelect.addEventListener('change', function() {
            toggleComparisonBrandsGroup(this.value);
        });
        // 初始化
        toggleComparisonBrandsGroup(contentTypeSelect.value);
    }
}

function toggleComparisonBrandsGroup(contentType) {
    const group = document.getElementById('comparisonBrandsGroup');
    if (group) {
        group.style.display = contentType === 'comparison' ? 'block' : 'none';
    }
}

// 添加对比品牌
function addComparisonBrand() {
    const container = document.getElementById('comparisonBrandInputs');
    if (!container) return;

    const inputs = container.querySelectorAll('.comparison-brand-input');
    if (inputs.length >= 4) {
        alert('最多只能添加4个对比品牌');
        return;
    }

    const newInput = document.createElement('div');
    newInput.className = 'comparison-brand-input';
    newInput.style.cssText = 'display: flex; gap: 8px; margin-bottom: 8px;';
    newInput.innerHTML = `
        <input type="text" class="form-input comparison-brand" placeholder="例如: 星颜塑" style="flex: 1;">
        <button type="button" class="btn-small btn-danger" onclick="removeComparisonBrand(this)">删除</button>
    `;
    container.appendChild(newInput);

    // 显示所有删除按钮
    updateRemoveButtonsVisibility();
}

// 删除对比品牌
function removeComparisonBrand(btn) {
    const container = document.getElementById('comparisonBrandInputs');
    if (!container) return;

    const inputGroup = btn.parentElement;
    inputGroup.remove();

    updateRemoveButtonsVisibility();
}

// 更新删除按钮的可见性
function updateRemoveButtonsVisibility() {
    const container = document.getElementById('comparisonBrandInputs');
    if (!container) return;

    const inputs = container.querySelectorAll('.comparison-brand-input');
    const deleteBtns = container.querySelectorAll('.btn-danger');

    deleteBtns.forEach(btn => {
        btn.style.display = inputs.length > 1 ? 'inline-block' : 'none';
    });
}

// 获取对比品牌列表
function getComparisonBrands() {
    const inputs = document.querySelectorAll('.comparison-brand-input .comparison-brand');
    const brands = [];
    inputs.forEach(input => {
        const value = input.value.trim();
        if (value) {
            brands.push(value);
        }
    });
    return brands;
}

async function generateGEOContent() {
    if (!currentProjectId) return;
    const contentType = document.getElementById('geoContentType').value;
    const question = document.getElementById('geoContentTitle').value.trim();
    const brandName = document.getElementById('geoContentBrand').value.trim();
    const btn = event.target;
    const originalText = btn.textContent;

    if (!question) {
        alert('请输入或选择问题');
        return;
    }

    // 如果是横向对比文，检查对比品牌
    let competitorBrands = [];
    if (contentType === 'comparison') {
        competitorBrands = getComparisonBrands();
        if (competitorBrands.length === 0) {
            alert('请至少添加1个对比品牌');
            return;
        }
    }

    try {
        btn.textContent = '⏳ 正在检索素材...';
        btn.disabled = true;

        const requestBody = {
            project_id: currentProjectId,
            type: contentType,
            question,
            brand_name: brandName
        };

        // 如果是横向对比文，添加对比品牌
        if (contentType === 'comparison') {
            requestBody.competitor_brands = competitorBrands;
        }

        const response = await fetch('/api/geo/content/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });

        btn.textContent = '⏳ 正在生成文章...';

        const data = await response.json();
        if (data.success) {
            document.getElementById('geoContentPreview').value = data.content;
            btn.textContent = '✅ 生成完成';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 1500);
        }
    } catch (error) {
        console.error('生成失败:', error);
        alert('生成失败');
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// ========== 关键词选择器 ==========

function openKeywordSelector() {
    if (!currentProjectId) return;

    // 重置筛选状态
    currentKeywordTierFilter = 'all';
    document.getElementById('keywordSelectorSearch').value = '';

    // 重置tab样式
    const tabs = document.querySelectorAll('#keywordSelectorTabs .geo-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    tabs[0].classList.add('active');

    document.getElementById('keywordSelectorModal').style.display = 'flex';
    loadKeywordsForSelector();
}

function closeKeywordSelector() {
    document.getElementById('keywordSelectorModal').style.display = 'none';
}

async function loadKeywordsForSelector() {
    if (!currentProjectId) return;
    try {
        const response = await fetch(`/api/geo/keywords?project_id=${currentProjectId}&page=1&page_size=1000`);
        const data = await response.json();
        if (data.success) {
            allKeywordsForSelector = data.keywords || [];
            renderKeywordSelectorList();
        }
    } catch (error) {
        console.error('加载关键词失败:', error);
    }
}

function renderKeywordSelectorList() {
    const listDiv = document.getElementById('keywordSelectorList');
    const searchText = document.getElementById('keywordSelectorSearch').value.toLowerCase().trim();

    let filtered = allKeywordsForSelector;

    // 按层级过滤
    if (currentKeywordTierFilter !== 'all') {
        filtered = filtered.filter(kw => kw.tier === currentKeywordTierFilter);
    }

    // 按搜索文本过滤
    if (searchText) {
        filtered = filtered.filter(kw => kw.keyword.toLowerCase().includes(searchText));
    }

    if (filtered.length === 0) {
        listDiv.innerHTML = '<div style="text-align:center;color:#999;padding:20px">没有找到关键词</div>';
        return;
    }

    const tierNames = {
        'brand': '品牌词',
        'accurate': '精准词',
        'generic': '大词',
        'scene': '场景词'
    };

    let html = '';
    for (const kw of filtered) {
        html += `
            <div class="geo-list-item" style="cursor:pointer;padding:12px;border-radius:8px;transition:background 0.2s"
                 onmouseover="this.style.background='#f0f0f0'"
                 onmouseout="this.style.background=''"
                 onclick="selectKeyword('${escapeHtml(kw.keyword)}')">
                <div style="font-weight:500">${escapeHtml(kw.keyword)}</div>
                <div style="font-size:0.85em;color:#666;margin-top:4px">
                    <span class="geo-badge tier-${kw.tier}">${tierNames[kw.tier]}</span>
                    ${kw.is_target ? '<span class="geo-badge target" style="background:#e6f7ff;color:#1890ff">核心目标</span>' : ''}
                </div>
            </div>
        `;
    }
    listDiv.innerHTML = html;
}

function filterKeywordSelector() {
    renderKeywordSelectorList();
}

function filterKeywordSelectorByTier(tier) {
    currentKeywordTierFilter = tier;

    // 更新tab样式
    const tabs = document.querySelectorAll('#keywordSelectorTabs .geo-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');

    renderKeywordSelectorList();
}

function selectKeyword(keyword) {
    document.getElementById('geoContentTitle').value = keyword;
    closeKeywordSelector();
}

async function checkGeoContent() {
    const content = document.getElementById('geoContentPreview').value;
    if (!content) {
        alert('请先生成内容');
        return;
    }

    try {
        const response = await fetch('/api/geo/content/check', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content})
        });
        const data = await response.json();
        if (data.success) {
            const resultDiv = document.getElementById('geoCheckResult');
            resultDiv.innerHTML = `
                <div class="${data.passed ? 'check-pass' : 'check-fail'}" style="font-weight:bold;margin-bottom:8px">
                    ${data.passed ? '✓ 通过 GEO 规范检查' : '✗ 需要改进'}
                </div>
                ${data.issues.length > 0 ? `
                    <ul>
                        ${data.issues.map(i => `<li>${i}</li>`).join('')}
                    </ul>
                ` : ''}
            `;
        }
    } catch (error) {
        console.error('检查失败:', error);
    }
}

async function scoreGeoContent() {
    const content = document.getElementById('geoContentPreview').value;
    const brandName = document.getElementById('geoContentBrand').value;
    if (!content) {
        alert('请先生成内容');
        return;
    }

    const resultDiv = document.getElementById('geoScoreResult');
    resultDiv.innerHTML = '<div style="color:#667eea">⏳ 正在评分...</div>';

    try {
        const response = await fetch('/api/geo/content/score', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content, brand_name: brandName || null})
        });
        const data = await response.json();
        if (data.success) {
            const result = data.result;
            const gradeColor = getGradeColor(result.grade);

            let dimensionsHtml = '';
            for (const [key, dim] of Object.entries(result.dimensions)) {
                const dimColor = dim.score >= 80 ? '#22c55e' : dim.score >= 60 ? '#f59e0b' : '#ef4444';
                dimensionsHtml += `
                    <div style="margin-bottom:10px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                            <span style="color:#444;">${dim.name}</span>
                            <span style="color:${dimColor};font-weight:bold;">${dim.score}分</span>
                        </div>
                        <div style="background:#e5e7eb;height:8px;border-radius:4px;overflow:hidden;">
                            <div style="background:${dimColor};height:100%;width:${dim.score}%;border-radius:4px;"></div>
                        </div>
                    </div>
                `;
            }

            let feedbackHtml = '';
            if (result.all_feedback && result.all_feedback.length > 0) {
                feedbackHtml = `
                    <div style="margin-top:16px;">
                        <h4 style="margin-bottom:8px;color:#444;">💡 优化建议</h4>
                        <ul style="margin:0;padding-left:20px;color:#666;">
                            ${result.all_feedback.map(f => `<li style="margin-bottom:4px;">${escapeHtml(f)}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }

            resultDiv.innerHTML = `
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;">
                    <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">
                        <div style="width:80px;height:80px;border-radius:50%;background:${gradeColor};display:flex;flex-direction:column;align-items:center;justify-content:center;color:white;">
                            <span style="font-size:24px;font-weight:bold;">${result.overall_score}</span>
                            <span style="font-size:14px;">等级 ${result.grade}</span>
                        </div>
                        <div>
                            <div style="font-size:18px;font-weight:bold;color:#333;margin-bottom:4px;">
                                ${result.passed ? '✅ 内容质量良好' : '⚠️ 需要优化'}
                            </div>
                            <div style="color:#666;">${result.summary}</div>
                        </div>
                    </div>
                    <div style="border-top:1px solid #e2e8f0;padding-top:16px;">
                        <h4 style="margin-bottom:12px;color:#444;">📊 各维度评分</h4>
                        ${dimensionsHtml}
                    </div>
                    ${feedbackHtml}
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div style="color:#ef4444;">❌ 评分失败: ${escapeHtml(error.message)}</div>`;
        console.error('评分失败:', error);
    }
}

function getGradeColor(grade) {
    const colors = {
        'S': '#22c55e',
        'A': '#667eea',
        'B': '#f59e0b',
        'C': '#f97316',
        'D': '#ef4444'
    };
    return colors[grade] || '#999';
}

// ========== 竞品分析 ==========

async function loadCompetitorData() {
    if (!currentProjectId) return;
    try {
        const response = await fetch(`/api/geo/competitors?project_id=${currentProjectId}`);
        const data = await response.json();
        if (data.success) {
            renderCompetitors(data.competitors);
            renderGapAnalysis(data.gap);
        }
    } catch (error) {
        console.error('加载竞品数据失败:', error);
    }
}

function renderCompetitors(competitors) {
    const container = document.getElementById('geoCompetitorList');
    if (!competitors || competitors.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = competitors.map(comp => `
        <div class="geo-list-item geo-competitor-card">
            <div class="geo-list-header">
                <span class="geo-list-title">${escapeHtml(comp.name)}</span>
            </div>
            ${comp.url ? `<a href="${escapeHtml(comp.url)}" target="_blank" style="color:#667eea;text-decoration:none">${escapeHtml(comp.url)}</a>` : ''}
            ${comp.notes ? `<div style="margin-top:6px;color:#666">${escapeHtml(comp.notes)}</div>` : ''}
            <div class="geo-list-actions">
                <button class="btn-delete" onclick="deleteCompetitor(${comp.id})">🗑️ 删除</button>
            </div>
        </div>
    `).join('');
}

function renderGapAnalysis(gap) {
    const container = document.getElementById('geoGapAnalysis');
    if (!gap) {
        container.innerHTML = '';
        return;
    }

    let html = '';
    if (gap.gap_keywords && gap.gap_keywords.length > 0) {
        html += `
            <div class="geo-gap-highlight">
                <strong>空白关键词:</strong> ${gap.gap_keywords.map(k => escapeHtml(k)).join(' • ')}
            </div>
        `;
    }
    if (gap.suggestions) {
        html += `<div style="margin-top:10px;color:#666">${gap.suggestions.join('')}</div>`;
    }
    container.innerHTML = html;
}

// 豆包引用分页状态
let citationCurrentPage = 1;
let citationPageSize = 5;
let citationPaginationData = null;

async function loadDoubaoCitations(resetPage = true) {
    if (!currentProjectId) return;

    if (resetPage) {
        citationCurrentPage = 1;
    }

    const container = document.getElementById('doubaoCitationList');
    const paginationContainer = document.getElementById('doubaoCitationPagination');
    container.innerHTML = '<div style="text-align:center;padding:20px;">加载中...</div>';
    paginationContainer.innerHTML = '';

    const importFilter = document.getElementById('citationImportFilter')?.value || '';

    try {
        const params = new URLSearchParams({
            page: citationCurrentPage,
            page_size: citationPageSize,
            ...(importFilter && { import_filter: importFilter })
        });

        const response = await fetch(`/api/geo/doubao-citations/${currentProjectId}?${params}`);
        const data = await response.json();

        if (!data.success) {
            container.innerHTML = `<div style="color:#ef4444;">加载失败: ${data.error}</div>`;
            return;
        }

        citationPaginationData = data;

        if (!data.items || data.items.length === 0) {
            container.innerHTML = `
                <div style="background:#fffbea;padding:12px;border-radius:6px;border:1px solid #fde68a;">
                    <div style="font-weight:bold;color:#92400e;margin-bottom:8px;">💡 暂无引用链接</div>
                    <ol style="color:#78350f;margin:0;padding-left:20px;line-height:1.6;">
                        <li>去"任务控制"页面运行一次监测任务</li>
                        <li>如果豆包回答里有引用链接，会自动提取到这里</li>
                        <li>点击"导入"按钮抓取链接内容存文档库</li>
                    </ol>
                </div>
            `;
            return;
        }

        container.innerHTML = data.items.map(cite => `
            <div class="competitor-card" style="margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                            <span style="font-weight:bold;">📅 ${cite.date_str}</span>
                            ${cite.is_imported ? '<span style="background:#10b981;color:white;padding:2px 8px;border-radius:12px;font-size:0.8em;">已导入</span>' : ''}
                        </div>
                        <div style="color:#374151;margin-bottom:4px;">❓ ${escapeHtml(cite.question_text || '')}</div>
                        <div style="color:#6b7280;font-size:0.9em;word-break:break-all;margin-bottom:4px;">
                            🔗 <a href="${escapeHtml(cite.url)}" target="_blank" style="color:#3b82f6;">${escapeHtml(cite.url)}</a>
                        </div>
                        ${cite.context_snippet ? `<div style="color:#9ca3af;font-size:0.85em;background:#f3f4f6;padding:8px;border-radius:4px;">${escapeHtml(cite.context_snippet)}</div>` : ''}
                    </div>
                    <button class="btn-small btn-primary" onclick="importCitation(${cite.id})" ${cite.is_imported ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>
                        📥 导入
                    </button>
                </div>
            </div>
        `).join('');

        // 渲染分页
        renderCitationPagination();

    } catch (error) {
        container.innerHTML = `<div style="color:#ef4444;">加载失败: ${error.message}</div>`;
    }
}

function renderCitationPagination() {
    const container = document.getElementById('doubaoCitationPagination');
    if (!container || !citationPaginationData) return;

    const {page, page_size, total, total_pages} = citationPaginationData;

    if (total === 0) {
        container.innerHTML = '';
        return;
    }

    let html = '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;padding:8px 0;">';

    // 每页条数选择
    html += `
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="color:#666;font-size:0.9em;">每页:</span>
            <select onchange="changeCitationPageSize(this.value)" style="padding:4px 8px;border-radius:4px;border:1px solid #d1d5db;">
                <option value="5" ${citationPageSize === 5 ? 'selected' : ''}>5条</option>
                <option value="10" ${citationPageSize === 10 ? 'selected' : ''}>10条</option>
            </select>
        </div>
    `;

    // 分页信息
    const start = (page - 1) * page_size + 1;
    const end = Math.min(page * page_size, total);
    html += `<span style="color:#666;font-size:0.9em;">显示 ${start}-${end} 条，共 ${total} 条</span>`;

    // 分页按钮
    html += '<div style="display:flex;gap:4px;">';
    html += `<button class="btn-small btn-secondary" onclick="goToCitationPage(1)" ${page === 1 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>首页</button>`;
    html += `<button class="btn-small btn-secondary" onclick="goToCitationPage(${page - 1})" ${page === 1 ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>上一页</button>`;
    html += `<span style="color:#666;padding:4px 8px;font-size:0.9em;">第 ${page} / ${total_pages} 页</span>`;
    html += `<button class="btn-small btn-secondary" onclick="goToCitationPage(${page + 1})" ${page === total_pages ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>下一页</button>`;
    html += `<button class="btn-small btn-secondary" onclick="goToCitationPage(${total_pages})" ${page === total_pages ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>末页</button>`;
    html += '</div>';

    html += '</div>';
    container.innerHTML = html;
}

function goToCitationPage(page) {
    if (!citationPaginationData) return;
    if (page < 1 || page > citationPaginationData.total_pages) return;
    citationCurrentPage = page;
    loadDoubaoCitations(false);
}

function changeCitationPageSize(size) {
    citationPageSize = parseInt(size);
    citationCurrentPage = 1;
    loadDoubaoCitations(false);
}

async function importCitation(citationId) {
    if (!currentProjectId) return;

    try {
        const response = await fetch(`/api/geo/doubao-citations/${currentProjectId}/${citationId}/import`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            alert('✅ 已导入到文档库！');
            loadDoubaoCitations(citationCurrentPage); // 刷新当前页
        } else {
            alert('导入失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        alert('导入失败: ' + error.message);
    }
}

async function manualImportUrl() {
    const urlInput = document.getElementById('manualImportUrl');
    const url = urlInput.value.trim();

    if (!url) {
        alert('请输入URL');
        return;
    }

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        alert('URL必须以 http:// 或 https:// 开头');
        return;
    }

    // 从URL中提取标题（用域名作为默认标题）
    let title = '';
    try {
        const urlObj = new URL(url);
        title = urlObj.hostname;
    } catch {
        title = '导入的文章';
    }

    await importCitationToDocs(url, title);

    // 清空输入框
    urlInput.value = '';
}

async function importCitationToDocs(url, title) {
    if (!confirm(`确定要导入这个链接到文档库吗？\n\n${title || url}`)) {
        return;
    }

    try {
        const response = await fetch('/api/geo/citations/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: url,
                title: title,
                project_id: currentProjectId
            })
        });

        const data = await response.json();
        if (data.success) {
            alert(`✅ 导入成功！\n\n已保存到文档库。\n\n内容预览: ${data.content_preview || ''}`);
        } else {
            alert(`❌ 导入失败: ${data.error || '未知错误'}`);
        }
    } catch (error) {
        alert(`❌ 导入失败: ${error.message}`);
    }
}

async function analyzeDoubaoCitations() {
    const citations = window.currentCitations || [];
    const resultDiv = document.getElementById('citationAnalysisResult');

    if (citations.length === 0) {
        alert('请先加载引用数据');
        return;
    }

    resultDiv.innerHTML = '<div style="color:#667eea">⏳ 正在分析...</div>';

    try {
        const response = await fetch('/api/geo/citations/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({citations, use_llm: true})
        });
        const data = await response.json();
        if (data.success) {
            resultDiv.innerHTML = data.html_report || '<div style="color:#22c55e;">✅ 分析完成</div>';
        } else {
            resultDiv.innerHTML = `<div style="color:#ef4444;">❌ 分析失败: ${escapeHtml(data.error || '')}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div style="color:#ef4444;">❌ 分析失败: ${escapeHtml(error.message)}</div>`;
        console.error('分析失败:', error);
    }
}

function openAddCompetitorModal() {
    document.getElementById('newCompetitorName').value = '';
    document.getElementById('newCompetitorUrl').value = '';
    document.getElementById('newCompetitorNotes').value = '';
    document.getElementById('addCompetitorModal').style.display = 'flex';
}

function closeAddCompetitorModal() {
    document.getElementById('addCompetitorModal').style.display = 'none';
}

async function saveCompetitor() {
    if (!currentProjectId) return;
    const name = document.getElementById('newCompetitorName').value.trim();
    const url = document.getElementById('newCompetitorUrl').value.trim();
    const notes = document.getElementById('newCompetitorNotes').value.trim();

    if (!name) {
        alert('请输入竞品名称');
        return;
    }

    try {
        const response = await fetch('/api/geo/competitors', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_id: currentProjectId,
                name, url, notes
            })
        });
        const data = await response.json();
        if (data.success) {
            closeAddCompetitorModal();
            loadCompetitorData();
        } else {
            alert('保存失败: ' + data.error);
        }
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败');
    }
}

async function deleteCompetitor(id) {
    if (!confirm('确定要删除这个竞品吗？')) return;
    try {
        const response = await fetch(`/api/geo/competitors/${id}`, {method: 'DELETE'});
        const data = await response.json();
        if (data.success) {
            loadCompetitorData();
        }
    } catch (error) {
        console.error('删除失败:', error);
    }
}

// 弹窗关闭事件
document.addEventListener('click', (e) => {
    if (e.target.id === 'addKeywordModal') closeAddKeywordModal();
    if (e.target.id === 'keywordGenModal') closeKeywordGenModal();
    if (e.target.id === 'uploadDocumentModal') closeUploadDocumentModal();
    if (e.target.id === 'createSummaryModal') closeCreateSummaryModal();
    if (e.target.id === 'viewDocumentModal') closeViewDocumentModal();
    if (e.target.id === 'keywordSelectorModal') closeKeywordSelector();
    if (e.target.id === 'addCompetitorModal') closeAddCompetitorModal();
});
