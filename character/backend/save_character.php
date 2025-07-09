<?php
require_once 'db_config.php';
setCorsHeaders();
header('Content-Type: application/json');

try {
    $conn = getDbConnection(); 

    $input = json_decode(file_get_contents('php://input'), true);

    $characterName = $input['name'] ?? null;
    $characterDescription = $input['description'] ?? null;
    $aiAnalysis = $input['ai_analysis'] ?? null;
    $wins = $input['wins'] ?? 0;   
    $losses = $input['losses'] ?? 0;

    if (empty($characterName) || empty($characterDescription)) {
        echo json_encode(["success" => false, "message" => "캐릭터 이름과 설명은 필수입니다."]);
        exit();
    }

    $stmt = $conn->prepare("INSERT INTO characters (name, description, ai_analysis, wins, losses) VALUES (?, ?, ?, ?, ?)");
    $stmt->bind_param("sssii", $characterName, $characterDescription, $aiAnalysis, $wins, $losses);

    if ($stmt->execute()) {
        echo json_encode(["success" => true, "message" => "캐릭터 정보가 성공적으로 저장되었습니다."]);
    } else {
        error_log("SQL Error (save_character.php): " . $stmt->error);
        throw new Exception("데이터 저장 실패: " . $stmt->error);
    }

    $stmt->close();
    $conn->close();

} catch (Exception $e) {
    echo json_encode(["success" => false, "message" => $e->getMessage()]);
}
?>
