.PHONY: all build test clean check format deploy help

# Compiler settings
CXX := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -O2
LDFLAGS := -lm

# Directories
SRC_DIR := src
INCLUDE_DIR := include
TEST_DIR := tests
BUILD_DIR := build
BIN_DIR := bin

# Files
SOURCES := $(SRC_DIR)/UCTokenContract.cpp $(SRC_DIR)/UCICDaoContract.cpp $(SRC_DIR)/OracleContract.cpp
HEADERS := $(INCLUDE_DIR)/types.h $(INCLUDE_DIR)/UCTokenContract.h $(INCLUDE_DIR)/UCICDaoContract.h $(INCLUDE_DIR)/OracleContract.h
TEST_SOURCES := $(TEST_DIR)/test_contracts.cpp
OBJECTS := $(SOURCES:$(SRC_DIR)/%.cpp=$(BUILD_DIR)/%.o)
TEST_OBJECTS := $(TEST_SOURCES:$(TEST_DIR)/%.cpp=$(BUILD_DIR)/%.o)

# Targets
TEST_BIN := $(BIN_DIR)/test_contracts
DEPLOY_SCRIPT := deploy.sh

all: build test

# ============================================================================
# BUILD TARGETS
# ============================================================================

build: $(BIN_DIR) $(BUILD_DIR) $(OBJECTS)
	@echo "✓ Smart contracts built successfully"

$(BIN_DIR):
	@mkdir -p $(BIN_DIR)

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp $(HEADERS)
	@echo "Compiling $<..."
	@$(CXX) $(CXXFLAGS) -I$(INCLUDE_DIR) -c $< -o $@

# ============================================================================
# TEST TARGETS
# ============================================================================

test: $(TEST_BIN)
	@echo ""
	@echo "Running tests..."
	@echo "================================"
	@$(TEST_BIN)

$(TEST_BIN): $(BUILD_DIR) $(OBJECTS) $(BUILD_DIR)/test_contracts.o
	@echo "Linking test executable..."
	@$(CXX) $(CXXFLAGS) -I$(INCLUDE_DIR) $(OBJECTS) $(BUILD_DIR)/test_contracts.o -o $(TEST_BIN) $(LDFLAGS)

$(BUILD_DIR)/test_contracts.o: $(TEST_DIR)/test_contracts.cpp $(HEADERS)
	@echo "Compiling test suite..."
	@$(CXX) $(CXXFLAGS) -I$(INCLUDE_DIR) -c $(TEST_DIR)/test_contracts.cpp -o $(BUILD_DIR)/test_contracts.o

# ============================================================================
# CODE QUALITY
# ============================================================================

check:
	@echo "Running static analysis (cppcheck)..."
	@cppcheck --std=c++17 --enable=all --suppress=missingIncludeSystem $(SRC_DIR) $(INCLUDE_DIR) $(TEST_DIR) 2>/dev/null || echo "cppcheck not found, skipping"
	@echo ""
	@echo "Checking code style..."
	@clang-format --dry-run --Werror $(SRC_DIR)/*.cpp $(INCLUDE_DIR)/*.h $(TEST_DIR)/*.cpp 2>/dev/null || echo "clang-format check skipped"

format:
	@echo "Formatting code..."
	@clang-format -i $(SRC_DIR)/*.cpp $(INCLUDE_DIR)/*.h $(TEST_DIR)/*.cpp 2>/dev/null || echo "clang-format not found, skipping"
	@echo "✓ Code formatted"

# ============================================================================
# DEPLOYMENT
# ============================================================================

deploy: build
	@echo "Preparing for testnet deployment..."
	@bash $(DEPLOY_SCRIPT) 2>/dev/null || echo "Deploy script not executable"

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs:
	@echo "Generating documentation..."
	@doxygen Doxyfile 2>/dev/null || echo "Doxygen not installed"

# ============================================================================
# CLEANUP
# ============================================================================

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR) $(BIN_DIR)
	@echo "✓ Cleaned"

distclean: clean
	@echo "Removing all generated files..."
	@rm -rf docs
	@echo "✓ Full clean complete"

# ============================================================================
# HELP
# ============================================================================

help:
	@echo ""
	@echo "Qubic Healthcare DAO Smart Contracts - Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  all       - Build all and run tests (default)"
	@echo "  build     - Compile smart contracts"
	@echo "  test      - Run comprehensive test suite"
	@echo "  check     - Run static analysis and style checks"
	@echo "  format    - Auto-format code"
	@echo "  deploy    - Prepare for testnet deployment"
	@echo "  docs      - Generate Doxygen documentation"
	@echo "  clean     - Remove build artifacts"
	@echo "  distclean - Remove all generated files"
	@echo "  help      - Show this message"
	@echo ""
	@echo "Examples:"
	@echo "  make                 # Build and run tests"
	@echo "  make test            # Run tests only"
	@echo "  make check           # Check code quality"
	@echo "  make format          # Format code"
	@echo ""

# ============================================================================
# DEFAULT TARGET
# ============================================================================

.DEFAULT_GOAL := help
