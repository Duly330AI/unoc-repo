# Proto Generation Makefile
# Single source of truth: /unoc/proto/ contains all .proto files
# Generated files: backend/proto/ (Python), engine-go/proto/ (Go)

# Directories
PROTO_DIR := .
BACKEND_PROTO_DIR := ../backend/proto
GO_PROTO_DIR := ../engine-go/proto

# Proto files
BATCH_PROTO := $(PROTO_DIR)/batch/batch.proto
OPTICAL_PROTO := $(PROTO_DIR)/optical/optical.proto
STATUS_PROTO := $(PROTO_DIR)/status/status.proto

# Tools
PROTOC := protoc
PROTOC_GEN_GO := protoc-gen-go
PROTOC_GEN_GO_GRPC := protoc-gen-go-grpc

.PHONY: all generate-go generate-python clean help

# Default target: generate all stubs
all: generate-go generate-python
	@echo "✅ All proto stubs generated successfully"

# Generate Go stubs (engine-go)
generate-go: generate-go-batch generate-go-optical generate-go-status
	@echo "✅ Go stubs generated in $(GO_PROTO_DIR)"

generate-go-batch:
	@echo "🔧 Generating Go stubs for batch.proto..."
	$(PROTOC) --proto_path=$(PROTO_DIR) \
		--go_out=$(GO_PROTO_DIR) --go_opt=paths=source_relative \
		--go-grpc_out=$(GO_PROTO_DIR) --go-grpc_opt=paths=source_relative \
		$(BATCH_PROTO)

generate-go-optical:
	@echo "🔧 Generating Go stubs for optical.proto..."
	$(PROTOC) --proto_path=$(PROTO_DIR) \
		--go_out=$(GO_PROTO_DIR) --go_opt=paths=source_relative \
		--go-grpc_out=$(GO_PROTO_DIR) --go-grpc_opt=paths=source_relative \
		$(OPTICAL_PROTO)

generate-go-status:
	@echo "🔧 Generating Go stubs for status.proto..."
	$(PROTOC) --proto_path=$(PROTO_DIR) \
		--go_out=$(GO_PROTO_DIR) --go_opt=paths=source_relative \
		--go-grpc_out=$(GO_PROTO_DIR) --go-grpc_opt=paths=source_relative \
		$(STATUS_PROTO)

# Generate Python stubs (backend)
generate-python: generate-python-batch generate-python-optical generate-python-status
	@echo "✅ Python stubs generated in $(BACKEND_PROTO_DIR)"

generate-python-batch:
	@echo "🔧 Generating Python stubs for batch.proto..."
	$(PROTOC) --proto_path=$(PROTO_DIR) \
		--python_out=$(BACKEND_PROTO_DIR) \
		--pyi_out=$(BACKEND_PROTO_DIR) \
		--grpc_python_out=$(BACKEND_PROTO_DIR) \
		$(BATCH_PROTO)

generate-python-optical:
	@echo "🔧 Generating Python stubs for optical.proto..."
	$(PROTOC) --proto_path=$(PROTO_DIR) \
		--python_out=$(BACKEND_PROTO_DIR) \
		--pyi_out=$(BACKEND_PROTO_DIR) \
		--grpc_python_out=$(BACKEND_PROTO_DIR) \
		$(OPTICAL_PROTO)

generate-python-status:
	@echo "🔧 Generating Python stubs for status.proto..."
	$(PROTOC) --proto_path=$(PROTO_DIR) \
		--python_out=$(BACKEND_PROTO_DIR) \
		--pyi_out=$(BACKEND_PROTO_DIR) \
		--grpc_python_out=$(BACKEND_PROTO_DIR) \
		$(STATUS_PROTO)

# Clean generated files
clean:
	@echo "🧹 Cleaning generated Go stubs..."
	rm -f $(GO_PROTO_DIR)/batch/*.pb.go
	rm -f $(GO_PROTO_DIR)/optical/*.pb.go
	rm -f $(GO_PROTO_DIR)/status/*.pb.go
	rm -f $(GO_PROTO_DIR)/optical.pb.go $(GO_PROTO_DIR)/optical_grpc.pb.go
	rm -f $(GO_PROTO_DIR)/status.pb.go $(GO_PROTO_DIR)/status_grpc.pb.go
	@echo "🧹 Cleaning generated Python stubs..."
	rm -f $(BACKEND_PROTO_DIR)/batch/*_pb2.py $(BACKEND_PROTO_DIR)/batch/*_pb2.pyi $(BACKEND_PROTO_DIR)/batch/*_pb2_grpc.py
	rm -f $(BACKEND_PROTO_DIR)/optical/*_pb2.py $(BACKEND_PROTO_DIR)/optical/*_pb2.pyi $(BACKEND_PROTO_DIR)/optical/*_pb2_grpc.py
	rm -f $(BACKEND_PROTO_DIR)/status/*_pb2.py $(BACKEND_PROTO_DIR)/status/*_pb2.pyi $(BACKEND_PROTO_DIR)/status/*_pb2_grpc.py
	@echo "✅ Clean complete"

# Help target
help:
	@echo "Proto Generation Makefile"
	@echo "========================="
	@echo ""
	@echo "Targets:"
	@echo "  all              - Generate all Go and Python stubs (default)"
	@echo "  generate-go      - Generate Go stubs for all protos"
	@echo "  generate-python  - Generate Python stubs for all protos"
	@echo "  clean            - Remove all generated stub files"
	@echo "  help             - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make                    # Generate all stubs"
	@echo "  make generate-go        # Generate only Go stubs"
	@echo "  make generate-python    # Generate only Python stubs"
	@echo "  make clean              # Clean generated files"
	@echo ""
	@echo "Requirements:"
	@echo "  - protoc (Protocol Buffer compiler)"
	@echo "  - protoc-gen-go (Go plugin)"
	@echo "  - protoc-gen-go-grpc (Go gRPC plugin)"
	@echo "  - grpcio-tools (Python: pip install grpcio-tools)"
	@echo ""
	@echo "Workflow:"
	@echo "  1. Edit .proto files in proto/batch/, proto/optical/, proto/status/"
	@echo "  2. Run 'make' to regenerate stubs"
	@echo "  3. Commit both source .proto files and generated stubs"
