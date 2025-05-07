// Dashboard JavaScript for Study Bot

document.addEventListener('DOMContentLoaded', function() {
    // عرض مؤشر التحميل
    const loader = document.getElementById('page-loader');
    
    // دالة لإظهار مؤشر التحميل
    function showLoader() {
        loader.style.display = 'flex';
    }
    
    // دالة لإخفاء مؤشر التحميل
    function hideLoader() {
        loader.style.display = 'none';
    }
    
    // تحميل البيانات الإحصائية
    function loadStats() {
        showLoader();
        
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                // تحديث إحصائيات المستخدمين
                document.getElementById('total-users').textContent = data.users.total;
                document.getElementById('active-users').textContent = data.users.active;
                document.getElementById('total-groups').textContent = data.users.groups;
                
                // تحديث إحصائيات الجداول
                document.getElementById('morning-users').textContent = data.schedules.morning;
                document.getElementById('evening-users').textContent = data.schedules.evening;
                document.getElementById('custom-users').textContent = data.schedules.custom;
                document.getElementById('no-schedule-users').textContent = data.schedules.none;
                
                // تحديث إحصائيات النقاط
                document.getElementById('total-points').textContent = data.points.total;
                
                // تحديث إحصائيات الإنجازات
                document.getElementById('completed-days').textContent = data.achievements.completed_days;
                document.getElementById('avg-points').textContent = data.achievements.avg_points;
                
                // تحديث قائمة أفضل المستخدمين
                updateTopUsers(data.achievements.top_users);
                
                // رسم المخططات البيانية
                drawActivityChart(data.activity);
                drawSchedulesChart(data.schedules);
                drawTasksCompletionChart(data.achievements);
                
                hideLoader();
            })
            .catch(error => {
                console.error('خطأ في تحميل البيانات:', error);
                hideLoader();
                
                // عرض رسالة خطأ للمستخدم
                alert('حدث خطأ أثناء تحميل البيانات. الرجاء المحاولة مرة أخرى لاحقاً.');
            });
    }
    
    // تحديث قائمة أفضل المستخدمين
    function updateTopUsers(users) {
        const topUsersList = document.getElementById('top-users-list');
        topUsersList.innerHTML = '';
        
        users.forEach(user => {
            const userItem = document.createElement('div');
            userItem.className = 'top-user-item';
            
            userItem.innerHTML = `
                <span class="top-user-name">${user.name}</span>
                <span class="top-user-points">${user.points} نقطة</span>
            `;
            
            topUsersList.appendChild(userItem);
        });
    }
    
    // رسم مخطط نشاط المستخدمين
    function drawActivityChart(activityData) {
        const ctx = document.getElementById('activity-chart').getContext('2d');
        
        // ترتيب البيانات حسب التاريخ (من الأقدم للأحدث)
        activityData.sort((a, b) => new Date(a.date) - new Date(b.date));
        
        const labels = activityData.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('ar-SA', { weekday: 'short', month: 'short', day: 'numeric' });
        });
        
        const studyData = activityData.map(item => item.study);
        const prayerData = activityData.map(item => item.prayer);
        const otherData = activityData.map(item => item.other);
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'الدراسة',
                        data: studyData,
                        borderColor: '#4caf50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.2,
                        fill: true
                    },
                    {
                        label: 'الصلاة',
                        data: prayerData,
                        borderColor: '#2196f3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.2,
                        fill: true
                    },
                    {
                        label: 'أخرى',
                        data: otherData,
                        borderColor: '#ff9800',
                        backgroundColor: 'rgba(255, 152, 0, 0.1)',
                        tension: 0.2,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'عدد النشاطات'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'اليوم'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'نشاط المستخدمين خلال الأسبوع الماضي'
                    },
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }
    
    // رسم مخطط توزيع الجداول
    function drawSchedulesChart(schedules) {
        const ctx = document.getElementById('schedules-chart').getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['الجدول الصباحي', 'الجدول المسائي', 'جدول مخصص', 'بدون جدول'],
                datasets: [{
                    data: [
                        schedules.morning,
                        schedules.evening,
                        schedules.custom,
                        schedules.none
                    ],
                    backgroundColor: [
                        '#4caf50',
                        '#2196f3',
                        '#ff9800',
                        '#9e9e9e'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'توزيع استخدام الجداول'
                    },
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    // رسم مخطط إكمال المهام
    function drawTasksCompletionChart(achievements) {
        const ctx = document.getElementById('tasks-completion-chart').getContext('2d');
        
        // بيانات تجريبية لإكمال المهام - يمكن استبدالها ببيانات حقيقية
        const completionData = {
            labels: ['الصلاة', 'الدراسة', 'الوجبات', 'التقييم اليومي'],
            datasets: [{
                label: 'نسبة الإكمال',
                data: [85, 70, 90, 60],
                backgroundColor: [
                    'rgba(76, 175, 80, 0.7)',
                    'rgba(33, 150, 243, 0.7)',
                    'rgba(255, 152, 0, 0.7)',
                    'rgba(156, 39, 176, 0.7)'
                ],
                borderWidth: 1
            }]
        };
        
        new Chart(ctx, {
            type: 'bar',
            data: completionData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'نسبة الإكمال (%)'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'نسبة إكمال المهام'
                    },
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    // معالجة نموذج البث
    const broadcastForm = document.getElementById('broadcast-form');
    
    broadcastForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const messageInput = document.getElementById('broadcast-message');
        const message = messageInput.value.trim();
        const resultDiv = document.getElementById('broadcast-result');
        
        if (!message) {
            resultDiv.innerHTML = '<div class="alert alert-danger mt-3">يرجى كتابة نص الرسالة قبل الإرسال</div>';
            return;
        }
        
        showLoader();
        
        fetch('/api/broadcast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            hideLoader();
            
            if (data.error) {
                resultDiv.innerHTML = `<div class="alert alert-danger mt-3">${data.error}</div>`;
            } else {
                const successCount = data.success || 0;
                const failCount = data.fail || 0;
                
                resultDiv.innerHTML = `
                    <div class="alert alert-success mt-3">
                        تم إرسال الرسالة بنجاح إلى ${successCount} مستخدم.
                        ${failCount > 0 ? `<br>فشل الإرسال إلى ${failCount} مستخدم.` : ''}
                    </div>
                `;
                
                // مسح النص بعد الإرسال الناجح
                messageInput.value = '';
            }
        })
        .catch(error => {
            hideLoader();
            console.error('خطأ في إرسال الرسالة:', error);
            resultDiv.innerHTML = '<div class="alert alert-danger mt-3">حدث خطأ أثناء إرسال الرسالة. الرجاء المحاولة مرة أخرى لاحقاً.</div>';
        });
    });
    
    // تحميل البيانات عند تحميل الصفحة
    loadStats();
    
    // تحديث البيانات كل 30 ثانية
    setInterval(loadStats, 30000);
    
    // إضافة السنة الحالية في فوتر الصفحة
    const currentYear = new Date().getFullYear();
    document.querySelectorAll('.footer-year').forEach(el => {
        el.textContent = currentYear;
    });
});
