.PHONY: default run test help

default:
	@./hm

run:
	@./hm run

test:
	@./hm test

help:
	@echo "Các lệnh nhanh của dự án:"
	@echo "  make        hoặc ./hm       : Mở GDB sẵn sàng gỡ lỗi"
	@echo "  make run    hoặc ./hm run   : Khởi chạy thẳng vào điểm RDO đầu tiên"
	@echo "  make test   hoặc ./hm test  : Chạy bộ kiểm thử tự động 12 bài"
