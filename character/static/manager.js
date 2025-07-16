document.addEventListener('DOMContentLoaded', () => {
    const stopSchedulerButton = document.getElementById('stopSchedulerButton');
    const startSchedulerButton = document.getElementById('startSchedulerButton');
    const schedulerMessage = document.getElementById('schedulerMessage');
    const schedulerStatusText = document.getElementById('schedulerStatus');
    const loadCharactersButton = document.getElementById('loadCharactersButton');
    const characterListForDeletion = document.getElementById('characterListForDeletion');
    const deleteCharacterMessage = document.getElementById('deleteCharacterMessage');
    const FLASK_API_BASE_URL = window.location.origin;

    function showMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = 'message-box';
        if (isError) {
            element.classList.add('error');
        }
        element.style.display = 'block';
        setTimeout(() => {
            element.style.display = 'none';
            element.textContent = '';
        }, 5000);
    }

    async function updateSchedulerUI() {
        try {
            const response = await fetch(`${FLASK_API_BASE_URL}/api/admin/scheduler_status`);
            const data = await response.json();
            if (data.status === 'running') {
                schedulerStatusText.textContent = '상태: 실행 중';
                schedulerStatusText.className = 'running';
                startSchedulerButton.disabled = true;
                stopSchedulerButton.disabled = false;
            } else {
                schedulerStatusText.textContent = '상태: 중단됨';
                schedulerStatusText.className = 'stopped';
                startSchedulerButton.disabled = false;
                stopSchedulerButton.disabled = true;
            }
        } catch (error) {
            console.error('스케줄러 상태 불러오기 오류:', error);
            schedulerStatusText.textContent = '상태: 알 수 없음 (오류)';
            schedulerStatusText.className = 'error';
            startSchedulerButton.disabled = false;
            stopSchedulerButton.disabled = false;
        }
    }

    if (startSchedulerButton) {
        startSchedulerButton.addEventListener('click', async () => {
            startSchedulerButton.disabled = true;
            startSchedulerButton.textContent = '시작 중...';
            try {
                const response = await fetch(`${FLASK_API_BASE_URL}/api/admin/start_scheduler`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                const data = await response.json();
                if (data.success) {
                    showMessage(schedulerMessage, data.message);
                } else {
                    showMessage(schedulerMessage, data.message, true);
                }
                await updateSchedulerUI();
            } catch (error) {
                console.error('AI 스케줄러 시작 오류:', error);
                showMessage(schedulerMessage, `스케줄러 시작 요청 실패: ${error.message}`, true);
            } finally {
                startSchedulerButton.textContent = 'AI 스케줄러 시작';
            }
        });
    }

    if (stopSchedulerButton) {
        stopSchedulerButton.addEventListener('click', async () => {
            stopSchedulerButton.disabled = true;
            stopSchedulerButton.textContent = '중단 중...';
            try {
                const response = await fetch(`${FLASK_API_BASE_URL}/api/admin/stop_scheduler`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                const data = await response.json();
                if (data.success) {
                    showMessage(schedulerMessage, data.message);
                } else {
                    showMessage(schedulerMessage, data.message, true);
                }
                await updateSchedulerUI();
            } catch (error) {
                console.error('AI 스케줄러 중단 오류:', error);
                showMessage(schedulerMessage, `스케줄러 중단 요청 실패: ${error.message}`, true);
            } finally {
                stopSchedulerButton.textContent = 'AI 스케줄러 중단';
            }
        });
    }

    async function loadCharactersForDeletion() {
        characterListForDeletion.innerHTML = '<p class="loading-message">캐릭터 목록을 불러오는 중...</p><ul></ul>';
        try {
            const response = await fetch(`${FLASK_API_BASE_URL}/api/characters`);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`캐릭터 목록 로드 오류 (${response.status}): ${errorText}`);
            }
            const characters = await response.json();

            const ul = characterListForDeletion.querySelector('ul');
            ul.innerHTML = '';

            if (characters.length === 0) {
                characterListForDeletion.innerHTML = '<p class="loading-message">등록된 캐릭터가 없습니다.</p><ul></ul>';
            } else {
                characters.forEach(char => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <span>ID: ${char.id} - ${char.name} (승: ${char.wins}, 패: ${char.losses})</span>
                        <button class="delete-char-btn" data-char-id="${char.id}">삭제</button>
                    `;
                    ul.appendChild(li);
                });
            }
        } catch (error) {
            console.error('캐릭터 목록 불러오기 오류:', error);
            characterListForDeletion.innerHTML = `<p class="loading-message error" style="color: red;">캐릭터 목록을 불러오는 데 실패했습니다: ${error.message}</p><ul></ul>`;
        }
    }

    if (loadCharactersButton) {
        loadCharactersButton.addEventListener('click', loadCharactersForDeletion);
    }

    if (characterListForDeletion) {
        characterListForDeletion.addEventListener('click', async (event) => {
            const deleteButton = event.target.closest('.delete-char-btn');
            if (deleteButton) {
                const characterId = deleteButton.dataset.charId;
                if (confirm(`정말로 캐릭터 ID ${characterId}와 관련된 모든 전적을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
                    deleteButton.disabled = true;
                    deleteButton.textContent = '삭제 중...';
                    try {
                        const response = await fetch(`${FLASK_API_BASE_URL}/api/admin/delete_character`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ id: characterId }),
                        });
                        const data = await response.json();
                        if (data.success) {
                            showMessage(deleteCharacterMessage, data.message);
                            loadCharactersForDeletion(); // 삭제 후 목록 새로고침
                        } else {
                            showMessage(deleteCharacterMessage, data.message, true);
                        }
                    } catch (error) {
                        console.error('캐릭터 삭제 오류:', error);
                        showMessage(deleteCharacterMessage, `캐릭터 삭제 요청 실패: ${error.message}`, true);
                    } finally {
                        deleteButton.disabled = false;
                        deleteButton.textContent = '삭제';
                    }
                }
            }
        });
    }

    const billboardTextSpan = document.getElementById('billboard-text');
    async function updateBillboard() {
        try {
            const response = await fetch(`${FLASK_API_BASE_URL}/api/latest_battle_log`);
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`전광판 API HTTP 오류 (${response.status}):`, errorText);
                billboardTextSpan.textContent = "배틀 소식 로드 오류: 서버 응답 문제";
                billboardTextSpan.style.animation = 'none';
                return;
            }
            
            let latestBattle;
            try {
                latestBattle = await response.json();
            } catch (jsonError) {
                console.error('전광판 데이터 JSON 파싱 오류:', jsonError, '응답 텍스트:', await response.text());
                billboardTextSpan.textContent = "배틀 소식 로드 오류: 데이터 형식 문제";
                billboardTextSpan.style.animation = 'none';
                return;
            }

            if (latestBattle && latestBattle.winner_name && latestBattle.loser_name && latestBattle.battle_reason) {
                let message = `${latestBattle.winner_name} (이)가 ${latestBattle.loser_name}(으)로부터 승리했습니다!`;
                if (latestBattle.battle_reason.includes('고전 끝에') || latestBattle.battle_reason.includes('치열한 접전 끝에')) {
                    message = `${latestBattle.winner_name} (이)가 ${latestBattle.loser_name} (을)를 고전 끝에 승리했습니다!`;
                } else if (latestBattle.battle_reason.includes('압도적인') || latestBattle.battle_reason.includes('손쉽게')) {
                    message = `${latestBattle.winner_name} (이)가 ${latestBattle.loser_name} (을)를 압도적으로 승리했습니다!`;
                }
                billboardTextSpan.textContent = message;
                billboardTextSpan.style.animation = 'none';
                void billboardTextSpan.offsetWidth;
                billboardTextSpan.style.animation = 'scroll-left 15s linear infinite';
            } else {
                billboardTextSpan.textContent = "새로운 배틀을 기다리는 중... 캐릭터를 생성해보세요!";
                billboardTextSpan.style.animation = 'none';
            }
        } catch (error) {
            console.error('전광판 데이터 불러오는 중 네트워크/예상치 못한 오류 발생:', error);
            billboardTextSpan.textContent = "배틀 소식을 불러오는 데 실패했습니다. (네트워크 오류)";
            billboardTextSpan.style.animation = 'none';
        }
    }

    if (billboardTextSpan) {
        updateBillboard();
        setInterval(updateBillboard, 15000); 
    }

    updateSchedulerUI();
});
