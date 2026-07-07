# PDF Portrait Splitter

지정한 폴더의 PDF 파일을 확인해서, 한 가로 페이지에 세로 2페이지가 좌우로 들어간 PDF를 실제 세로 페이지 2장으로 분리한 뒤 기존 파일명 그대로 저장하는 프로그램입니다.

글자 방향은 회전하지 않고 그대로 유지합니다. 이미 세로 방향인 PDF 페이지는 변환하지 않으며, 파일도 건드리지 않습니다.

## 설치

```powershell
python -m pip install -r requirements.txt
```

## 실행

폴더 선택 창으로 실행:

```powershell
python .\pdf_portrait_converter.py
```

특정 폴더를 바로 지정:

```powershell
python .\pdf_portrait_converter.py "D:\path\to\pdf-folder"
```

하위 폴더까지 포함:

```powershell
python .\pdf_portrait_converter.py "D:\path\to\pdf-folder" --recursive
```

변환되어 실제로 덮어쓴 PDF 파일명은 `modified_files.txt`에 한 줄씩 기록됩니다. 변환된 PDF가 없으면 파일은 비어 있습니다.

기존에 안내된 `pdf_landscape_converter.py`도 실행은 가능하지만, 내부적으로 새 세로 변환 프로그램을 호출합니다.
