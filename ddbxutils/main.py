# 직접 만든 ddbxutils 모듈 임포트
import ddbxutils

# 'next_day' 위젯의 기본값 가져오기
initial_value = ddbxutils.widgets.get("next_day")
print(f"초기 'next_day' 값: {initial_value}")

# 변경된 값 다시 가져오기
updated_value = ddbxutils.widgets.get("next_day")
print(f"업데이트된 'next_day' 값: {updated_value}")

# 존재하지 않는 위젯 가져오기
other_value = ddbxutils.widgets.get("another_widget")
print(f"'another_widget' 값: {other_value}")
