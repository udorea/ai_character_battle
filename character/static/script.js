document.addEventListener('DOMContentLoaded', () => {
    const analyzeButton = document.getElementById('analyzeButton');
    const resetButton = document.getElementById('resetButton');
    const characterNameInput = document.getElementById('characterName');
    const characterDescriptionTextarea = document.getElementById('characterDescription');
    const inputSection = document.querySelector('.input-section');
    const resultSection = document.querySelector('.result-section');
    const aiCharacterDescription = document.getElementById('aiCharacterDescription');

    const billboardTextSpan = document.getElementById('billboard-text');
    const PHP_API_BASE_URL = "http://localhost/CHARACTER/backend";
    const FLASK_API_BASE_URL = window.location.origin; 

    async function updateBillboard() {
        try {
            const response = await fetch(`${PHP_API_BASE_URL}/get_latest_battle_log.php`);
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`전광판 PHP API HTTP 오류 (${response.status}):`, errorText);
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
                let message = `${latestBattle.winner_name} (이)가 ${latestBattle.loser_name}으로부터 승리했습니다!`;
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

    if (analyzeButton) {
        analyzeButton.addEventListener('click', async () => {
            const characterName = characterNameInput.value.trim();
            const characterDescription = characterDescriptionTextarea.value.trim();

            if (!characterName || !characterDescription) {
                alert('캐릭터 이름과 소개를 모두 입력해주세요.'); 
                return;
            }

            analyzeButton.textContent = '분석 및 생성 중...';
            analyzeButton.disabled = true;

            try {
                const response = await fetch('/analyze_character', { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: characterName,
                        description: characterDescription
                    }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    if (errorData.error && errorData.error.includes('사용할 수 없는 단어가 포함되어 있습니다')) {
                        alert(errorData.error);
                    } else {
                        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
                    return;
                }

                const data = await response.json();

                document.querySelector('.character-analysis h3').textContent = `[${characterName}] 분석:`;
                aiCharacterDescription.textContent = data.character_analysis;

                const battleResultDiv = document.querySelector('.battle-result');
                if (battleResultDiv) {
                    battleResultDiv.innerHTML = `
                        <h3>자동 배틀 대기 중:</h3>
                        <p>${characterName} 캐릭터가 랭킹에 등록되었으며, 1분마다 자동으로 다른 캐릭터와 배틀을 시작합니다!</p>
                        <p>랭킹 페이지에서 결과를 확인하세요.</p>
                    `;
                }
                
                inputSection.style.display = 'none';
                resultSection.style.display = 'block';

                if (billboardTextSpan) {
                    updateBillboard();
                }

            } catch (error) {
                console.error('캐릭터 생성 및 분석 중 오류 발생:', error);
                alert(`캐릭터 생성 및 분석 중 오류가 발생했습니다: ${error.message || error}. 잠시 후 다시 시도해주세요.`);
            } finally {
                analyzeButton.textContent = '캐릭터 분석 및 배틀 시작!';
                analyzeButton.disabled = false;
            }
        });
    }

    if (resetButton) {
        resetButton.addEventListener('click', () => {
            characterNameInput.value = '';
            characterDescriptionTextarea.value = '';
            resultSection.style.display = 'none';
            inputSection.style.display = 'block';
            aiCharacterDescription.textContent = '';
        });
    }

    const rankingListDiv = document.getElementById('rankingList');
    const latestBattleSummaryDiv = document.getElementById('latest-battle-summary'); 
    const characterBattleHistoryDiv = document.getElementById('characterBattleHistory');
    const historyTitle = document.getElementById('historyTitle');
    const historyContent = document.getElementById('historyContent');
    const closeHistoryButton = document.getElementById('closeHistoryButton');
    
    if (rankingListDiv && latestBattleSummaryDiv) {
        async function loadRankingData() {
            try {
                const rankingResponse = await fetch(`${FLASK_API_BASE_URL}/api/ranking`);
                if (!rankingResponse.ok) {
                    const errorBody = await rankingResponse.text();
                    console.error(`랭킹 Flask API HTTP 오류 (${rankingResponse.status}):`, errorBody);
                    rankingListDiv.innerHTML = '<p class="loading-message" style="color: red;">랭킹 데이터를 불러오는 데 실패했습니다 (서버 응답 문제)</p>';
                    latestBattleSummaryDiv.innerHTML = '<p style="color: red;">배틀 요약을 불러오는 데 실패했습니다.</p>';
                    return; 
                }
                
                let rankingData;
                try {
                    rankingData = await rankingResponse.json();
                } catch (jsonError) {
                    console.error('랭킹 데이터 JSON 파싱 오류:', jsonError, '응답 텍스트:', await rankingResponse.text());
                    rankingListDiv.innerHTML = '<p class="loading-message" style="color: red;">랭킹 데이터를 불러오는 데 실패했습니다 (데이터 형식 문제)</p>';
                    latestBattleSummaryDiv.innerHTML = '<p style="color: red;">배틀 요약을 불러오는 데 실패했습니다.</p>';
                    return;
                }

                if (rankingData.length === 0) {
                    rankingListDiv.innerHTML = '<p class="loading-message">아직 등록된 캐릭터가 없습니다. 캐릭터를 생성해보세요!</p>';
                } else {
                    let tableHtml = `
                        <table class="ranking-table">
                            <thead>
                                <tr>
                                    <th>순위</th>
                                    <th>캐릭터 이름</th>
                                    <th>승</th>
                                    <th>패</th>
                                    <th>승률</th>
                                    <th>총 전투</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    rankingData.forEach(char => {
                        let rankClass = 'rank-default';
                        if (char.rank === 1) {
                            rankClass = 'rank-gold';
                        } else if (char.rank === 2) {
                            rankClass = 'rank-silver';
                        } else if (char.rank === 3) {
                            rankClass = 'rank-bronze';
                        }

                        tableHtml += `
                            <tr>
                                <td class="rank ${rankClass}">${char.rank}</td>
                                <td class="clickable-character-name" data-character-id="${char.id}" data-character-name="${char.name}">${char.name}</td>
                                <td>${char.wins}</td>
                                <td>${char.losses}</td>
                                <td>${char.win_rate}</td>
                                <td>${char.total_battles}</td>
                            </tr>
                        `;
                    });
                    tableHtml += `
                            </tbody>
                        </table>
                    `;
                    rankingListDiv.innerHTML = tableHtml;
                }

                const battleLogResponse = await fetch(`${PHP_API_BASE_URL}/get_latest_battle_log.php`);
                if (!battleLogResponse.ok) {
                    const errorBody = await battleLogResponse.text();
                    console.error(`최신 배틀 PHP API HTTP 오류 (${battleLogResponse.status}):`, errorBody);
                    latestBattleSummaryDiv.innerHTML = '<p style="color: red;">최근 배틀 정보 로드 오류: 서버 응답 문제</p>';
                    return; 
                }

                let latestBattle;
                try {
                    latestBattle = await battleLogResponse.json();
                } catch (jsonError) {
                    console.error('최신 배틀 데이터 JSON 파싱 오류:', jsonError, '응답 텍스트:', await battleLogResponse.text());
                    latestBattleSummaryDiv.innerHTML = '<p style="color: red;">최근 배틀 정보 로드 오류: 데이터 형식 문제</p>';
                    return;
                }

                if (latestBattle && latestBattle.winner_name && latestBattle.loser_name && latestBattle.battle_reason) {
                    latestBattleSummaryDiv.innerHTML = `
                        <p><strong>최근 배틀:</strong> ${latestBattle.winner_name} (이)가 ${latestBattle.loser_name}으로부터 승리했습니다!</p>
                        <p><strong>승리 이유:</strong> ${latestBattle.battle_reason}</p>
                    `;
                } else {
                    latestBattleSummaryDiv.innerHTML = '<p>아직 진행된 배틀이 없습니다.</p>';
                }

            } catch (error) {
                console.error('랭킹/배틀 요약 불러오는 중 네트워크/예상치 못한 오류 발생:', error);
                if (!rankingListDiv.innerHTML.includes('오류')) {
                    rankingListDiv.innerHTML = '<p class="loading-message" style="color: red;">랭킹 데이터를 불러오는 데 실패했습니다. (네트워크 오류)</p>';
                }
                if (!latestBattleSummaryDiv.innerHTML.includes('오류')) {
                    latestBattleSummaryDiv.innerHTML = '<p style="color: red;">배틀 요약을 불러오는 데 실패했습니다. (네트워크 오류)</p>';
                }
            }
        }

        loadRankingData();
        setInterval(loadRankingData, 30000);

        rankingListDiv.addEventListener('click', async (event) => {
            const clickedElement = event.target.closest('.clickable-character-name');
            if (clickedElement) {
                const characterId = clickedElement.dataset.characterId;
                const characterName = clickedElement.dataset.characterName;
                
                historyTitle.textContent = `${characterName}의 배틀 전적`;
                historyContent.innerHTML = '<p class="loading-message">전적을 불러오는 중...</p>';
                characterBattleHistoryDiv.style.display = 'block';
                
                try {
                    const response = await fetch(`${PHP_API_BASE_URL}/get_character_battles.php?id=${characterId}`);
                    if (!response.ok) {
                        const errorBody = await response.text();
                        console.error(`캐릭터 전적 PHP API HTTP 오류 (${response.status}):`, errorBody);
                        historyContent.innerHTML = '<p style="color: red;">전적을 불러오는 데 실패했습니다. (서버 응답 문제)</p>';
                        return;
                    }

                    let battles;
                    try {
                        battles = await response.json();
                    } catch (jsonError) {
                        console.error('캐릭터 전적 데이터 JSON 파싱 오류:', jsonError, '응답 텍스트:', await response.text());
                        historyContent.innerHTML = '<p style="color: red;">전적을 불러오는 데 실패했습니다. (데이터 형식 문제)</p>';
                        return;
                    }
                    
                    if (battles.length > 0) {
                        let historyHtml = '<ul>';
                        battles.forEach(battle => {
                            const battleDate = new Date(battle.timestamp).toLocaleString();
                            let resultText = '';
                            if (battle.winner_name === characterName) {
                                resultText = `<span style="color: #76FF03;">승리!</span> ${battle.loser_name}으로부터 승리했습니다.`;
                            } else if (battle.loser_name === characterName) {
                                resultText = `<span style="color: #FF4D4D;">패배...</span> ${battle.winner_name} (에게) 패배했습니다.`;
                            } else {
                                resultText = `알 수 없는 결과: ${battle.character1_name} vs ${battle.character2_name}`;
                            }
                            historyHtml += `
                                <li>
                                    <strong>${battleDate}:</strong> ${resultText}<br>
                                    <small>이유: ${battle.battle_reason}</small>
                                </li>
                            `;
                        });
                        historyHtml += '</ul>';
                        historyContent.innerHTML = historyHtml;
                    } else {
                        historyContent.innerHTML = '<p>아직 이 캐릭터의 배틀 전적이 없습니다.</p>';
                    }

                } catch (error) {
                    console.error('캐릭터 전적 불러오는 중 네트워크/예상치 못한 오류 발생:', error);
                    historyContent.innerHTML = '<p style="color: red;">전적을 불러오는 데 실패했습니다. (네트워크 오류)</p>';
                }
            }
        });

        if (closeHistoryButton) {
            closeHistoryButton.addEventListener('click', () => {
                characterBattleHistoryDiv.style.display = 'none';
                historyContent.innerHTML = '';
                historyTitle.textContent = '';
            });
        }
    }
});
