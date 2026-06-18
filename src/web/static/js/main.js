// GEO Brand Monitor - Dashboard JavaScript

let trendChart = null;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    loadSummary();
    loadTrend();

    // 每30秒刷新一次
    setInterval(() => {
        loadSummary();
        loadTrend();
    }, 30000);
});

// 初始化图表
function initChart() {
    const chartDom = document.getElementById('trendChart');
    trendChart = echarts.init(chartDom);

    window.addEventListener('resize', () => {
        trendChart.resize();
    });
}

// 加载汇总数据
async function loadSummary() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();

        document.getElementById('lastUpdated').textContent =
            `最后更新: ${data.last_updated}`;

        const summaries = data.summaries || [];
        const dates = summaries.map(s => s.date_str);

        // 更新统计卡片
        document.getElementById('totalDays').textContent = dates.length;

        // 计算平均提及率
        let totalQuestions = 0;
        let totalMentionCount = 0;
        summaries.forEach(s => {
            totalQuestions += s.total_questions || 0;
            totalMentionCount += s.brand_mentioned_count || 0;
        });

        const avgRate = totalQuestions > 0 ? Math.round((totalMentionCount / totalQuestions) * 100) : 0;
        document.getElementById('mentionRate').textContent = avgRate + '%';
        document.getElementById('totalQuestions').textContent = totalQuestions;

        // 渲染日期列表
        renderDateList(dates, summaries);
    } catch (error) {
        console.error('加载汇总数据失败:', error);
    }
}

// 渲染日期列表
function renderDateList(dates, summaries) {
    const container = document.getElementById('dateList');

    if (dates.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>暂无数据</p>
                <p>请先用 GUI 工具采集一些数据</p>
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
                <div class="date-item-meta">
                    提及率: ${rate}% | ${totalQ}个问题
                </div>
            </div>
        `;
    }).join('');
}

// 加载趋势数据
async function loadTrend() {
    try {
        const response = await fetch('/api/trend');
        const data = await response.json();

        renderTrendChart(data.stats);
    } catch (error) {
        console.error('加载趋势数据失败:', error);
    }
}

// 渲染趋势图表
function renderTrendChart(stats) {
    if (!trendChart) return;

    const dates = stats.map(s => s.date_str);
    const mentionRates = stats.map(s => {
        if (s.question_count > 0) {
            return Math.round((s.mention_count / s.question_count) * 100);
        }
        return 0;
    });

    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: (params) => {
                const p = params[0];
                return `${formatDate(p.name)}<br/>提及率: ${p.value}%`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: dates.map(d => formatDate(d))
        },
        yAxis: {
            type: 'value',
            min: 0,
            max: 100,
            axisLabel: {
                formatter: '{value}%'
            }
        },
        series: [{
            name: '提及率',
            type: 'line',
            smooth: true,
            data: mentionRates,
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
                    { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
                ])
            },
            lineStyle: {
                color: '#667eea',
                width: 2
            },
            itemStyle: {
                color: '#667eea'
            }
        }]
    };

    trendChart.setOption(option);
}

// 显示详情
async function showDetail(dateStr) {
    try {
        const response = await fetch(`/api/daily/${dateStr}`);
        const data = await response.json();

        document.getElementById('detailSection').style.display = 'block';
        document.getElementById('detailDate').textContent = formatDate(dateStr);

        const container = document.getElementById('detailContent');

        if (data.tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>当天暂无数据</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <button class="back-btn" onclick="hideDetail()">← 返回</button>
            ${data.tasks.map(task => {
                return `
                    <div class="detail-item">
                        <div class="detail-item-header">
                            <span class="detail-hour">${task.hour}:00</span>
                            <span class="detail-time">${task.timestamp}</span>
                        </div>
                        <div class="detail-question-list">
                            ${task.questions.map(q => `
                                <div class="detail-question">
                                    <div class="detail-question-title">Q: ${escapeHtml(q.question_text)}</div>
                                    <div class="detail-question-response">
                                        A: ${escapeHtml(q.response_text || '(无回复)').substring(0, 300)}
                                        ${(q.response_text || '').length > 300 ? '...' : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }).join('')}
        `;

        // 滚动到详情区域
        document.getElementById('detailSection').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('加载详情失败:', error);
    }
}

// 隐藏详情
function hideDetail() {
    document.getElementById('detailSection').style.display = 'none';
}

// 辅助函数: 格式化日期
function formatDate(dateStr) {
    if (!dateStr) return '';
    const year = dateStr.substring(0, 4);
    const month = dateStr.substring(4, 6);
    const day = dateStr.substring(6, 8);
    return `${year}-${month}-${day}`;
}

// 辅助函数: HTML 转义
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
