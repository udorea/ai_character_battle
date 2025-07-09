<?php
require_once 'db_config.php';
setCorsHeaders();
header('Content-Type: application/json');

try {
    $conn = getDbConnection();

    $input = json_decode(file_get_contents('php://input'), true);

    $characterId = $input['id'] ?? null;
    $updateType = $input['type'] ?? null;

    if (empty($characterId) || !in_array($updateType, ['win', 'loss'])) {
        echo json_encode(["success" => false, "message" => "캐릭터 ID와 업데이트 타입(win/loss)은 필수입니다."]);
        exit();
    }

    if ($updateType === 'win') {
        $sql = "UPDATE characters SET wins = wins + 1 WHERE id = ?";
    } else { // 'loss'
        $sql = "UPDATE characters SET losses = losses + 1 WHERE id = ?";
    }

    $stmt = $conn->prepare($sql);
    $stmt->bind_param("i", $characterId); 

    if ($stmt->execute()) {
        echo json_encode(["success" => true, "message" => "캐릭터 스탯이 성공적으로 업데이트되었습니다."]);
    } else {
        error_log("SQL Error (update_character_stats.php): " . $stmt->error);
        throw new Exception("스탯 업데이트 실패: " . $stmt->error);
    }

    $stmt->close();
    $conn->close();

} catch (Exception $e) {
    echo json_encode(["success" => false, "message" => $e->getMessage()]);
}
?>
