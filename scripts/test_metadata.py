import os
import json
import pythoncom
import win32com.client


def get_ppt_metadata(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파워포인트 파일을 찾을 수 없습니다: {file_path}")

    # 여기서 한 번 절대 경로로 변환 + 디버그 출력
    abs_path = os.path.abspath(file_path)
    print(f"[DEBUG] 열려고 하는 파일 절대 경로: {abs_path}")

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"절대 경로에서도 파일을 찾을 수 없습니다: {abs_path}")

    pythoncom.CoInitialize()

    app = None
    presentation = None

    metadata = {
        "file_path": abs_path,
        "builtin_properties": {},
        "custom_properties": {},
    }

    try:
        app = win32com.client.Dispatch("PowerPoint.Application")

        # 여기서 abs_path 사용
        presentation = app.Presentations.Open(
            abs_path, ReadOnly=True, Untitled=False, WithWindow=False
        )

        for prop in presentation.BuiltInDocumentProperties:
            name = prop.Name
            try:
                value = prop.Value
            except Exception:
                value = None
            metadata["builtin_properties"][name] = value

        for prop in presentation.CustomDocumentProperties:
            name = prop.Name
            try:
                value = prop.Value
            except Exception:
                value = None
            metadata["custom_properties"][name] = value

    finally:
        if presentation is not None:
            presentation.Close()
        if app is not None:
            app.Quit()
        pythoncom.CoUninitialize()

    return metadata


if __name__ == "__main__":
    # 테스트용 파일 경로 (직접 수정해서 사용)
    ppt_path = r".\samples\250215_GenerativeModels.pptx"

    meta = get_ppt_metadata(ppt_path)

    # 보기 좋게 출력
    print(json.dumps(meta, indent=4, ensure_ascii=False, default=str))
