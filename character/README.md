# AI 캐릭터 배틀
___
1. ```<a href="{{ url_for('character_creator') }}"></a>```처럼 
웹페이지 이동 하이퍼링크가 이렇게 되어있습니다 이게 왜 그렇냐면 python flask를 쓸 때 ```<a href="../templates/index.html"></a>```이렇게 하면 이동이 안되더라구요 라우팅 때문인 것 같습니다 확인해주세요.

2. .env에 있는 GOOGLE_API_KEY 는 본인 GEMINI API 키를 가져와야합니다.

3. app.py에 있는 FORBIDDEN_WORDS 에 금칙어를 적을 수 있습니다.

4. app.py에서 포트설정이 app.run(host='0.0.0.0', port=5000, debug=True) 이렇게 되어있습니다 참고바랍니다.

5. db_config.php에 "#" 은 본인 정보를 적으십시오.

6. db_config.php에 $dbname 은 제가 your_character_db.sql로 올려서 your_character_db 로 하셔서도 됩니다.

python flask와 PHP를 동시에 쓴 경험은 한 번도 없었는데 좋은 경험이였습니다.
