# 여행상품 선택 연동 검증 결과

- 모델: STT 생략(텍스트 입력), LLM `openai/gpt-oss-120b`
- 통과: **12 / 13**

| 결과 | 발화 | 화면 | 변환된 명령 | 응답(ms) |
|---|---|---|---|---|
| ✅ | 두 번째 거 보여줘 | list | `select {'tourId': 23}` | 1491 |
| ✅ | 첫 번째 상품 선택할게 | list | `select {'tourId': 11}` | 813 |
| ✅ | 마지막 거로 할게 | list | `select {'tourId': 42}` | 874 |
| ❌ | 발리 가는 거 보여줘 | list | `search {'keyword': '발리'}` | 917 |
| ✅ | 골프 여행 상세 보여줘 | list | `select {'tourId': 37}` | 720 |
| ✅ | 다섯 번째 거 보여줘 | list | `unknown {'message': '다섯 번째 상품이 없습니다'}` | 1230 |
| ✅ | 10월에 가는 100만원 이하 효도 여행 찾아줘 | list | `search {'theme': 'HEALING', 'maxPrice': 1000000, 'startDateFrom': '2026-10-01', 'startDateTo': '2026-10-31'}` | 1010 |
| ✅ | 허니문 상품만 보여줘 | list | `search {'theme': 'HONEYMOON'}` | 829 |
| ✅ | 그랜드로 하고 5성급 호텔로 바꿔줘 | configure | `configure {'tourLevel': 'GRAND', 'hotelGrade': 'FIVE_STAR'}` | 1016 |
| ✅ | 두 명이요 | configure | `configure {'guestCount': 2}` | 5014 |
| ✅ | 이걸로 예약할게 | configure | ` | pending {'action': 'checkout', 'message': '예약 신청 화면으로 이동할까요?'}` | 7198 |
| ✅ | 뒤로 가줘 | list | `back {}` | 8057 |
| ✅ | 오늘 점심 뭐 먹지 | list | `unknown {'message': '다시 말씀해 주세요'}` | 8605 |
