// create_test.go - Unit Tests for Batch Link Creation
// Week 3 Day 13: Test coverage for BatchCreateLinks
package batch

import (
	"context"
	"database/sql"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	pb "github.com/unoc/engine-go/proto/batch"
)

// setupTestService creates a test service with mock database
func setupTestService(t *testing.T) (*Service, sqlmock.Sqlmock, func()) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)

	logger := zerolog.Nop() // Silent logger for tests
	service := NewService(db, logger)

	cleanup := func() {
		db.Close()
	}

	return service, mock, cleanup
}

// TestBatchCreateLinksEmpty tests empty request (no links)
func TestBatchCreateLinksEmpty(t *testing.T) {
	service, _, cleanup := setupTestService(t)
	defer cleanup()

	ctx := context.Background()
	req := &pb.BatchCreateLinksRequest{
		Links:     []*pb.LinkCreateSpec{},
		RequestId: "test-empty",
	}

	resp, err := service.BatchCreateLinks(ctx, req)

	require.NoError(t, err)
	assert.Equal(t, int32(0), resp.TotalRequested)
	assert.Equal(t, int32(0), resp.TotalCreated)
	assert.Empty(t, resp.CreatedLinkIds)
	assert.Empty(t, resp.FailedLinks)
	assert.Equal(t, "test-empty", resp.RequestId)
}

// TestBatchCreateLinksSingle tests creating a single link
func TestBatchCreateLinksSingle(t *testing.T) {
	service, mock, cleanup := setupTestService(t)
	defer cleanup()

	ctx := context.Background()
	req := &pb.BatchCreateLinksRequest{
		Links: []*pb.LinkCreateSpec{
			{
				AInterfaceId: 1,
				BInterfaceId: 2,
				LengthKm:     1.5,
				Status:       "active",
			},
		},
		RequestId: "test-single",
	}

	// Expect transaction start
	mock.ExpectBegin()

	// Expect interface validation query
	mock.ExpectQuery(`SELECT id FROM interface WHERE id = ANY\(\$1\)`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"id"}).AddRow(1).AddRow(2))

	// Expect linked interfaces check
	mock.ExpectQuery(`SELECT interface_id FROM`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"interface_id"})) // No linked interfaces

	// Expect link insertion
	mock.ExpectQuery(`INSERT INTO link`).
		WithArgs(1, 2, 1.5, "active").
		WillReturnRows(sqlmock.NewRows([]string{"id"}).AddRow(100))

	// Expect commit
	mock.ExpectCommit()

	resp, err := service.BatchCreateLinks(ctx, req)

	require.NoError(t, err)
	assert.Equal(t, int32(1), resp.TotalRequested)
	assert.Equal(t, int32(1), resp.TotalCreated)
	assert.Equal(t, []int32{100}, resp.CreatedLinkIds)
	assert.Empty(t, resp.FailedLinks)
	assert.Equal(t, "test-single", resp.RequestId)

	// Verify all expectations were met
	err = mock.ExpectationsWereMet()
	assert.NoError(t, err)
}

// TestBatchCreateLinksMultiple tests creating 64 links (realistic scenario)
func TestBatchCreateLinksMultiple(t *testing.T) {
	service, mock, cleanup := setupTestService(t)
	defer cleanup()

	ctx := context.Background()

	// Create 64 link specs
	links := make([]*pb.LinkCreateSpec, 64)
	for i := 0; i < 64; i++ {
		links[i] = &pb.LinkCreateSpec{
			AInterfaceId: int32(i*2 + 1),
			BInterfaceId: int32(i*2 + 2),
			LengthKm:     float32(i) + 0.5,
			Status:       "active",
		}
	}

	req := &pb.BatchCreateLinksRequest{
		Links:     links,
		RequestId: "test-64-links",
	}

	// Expect transaction start
	mock.ExpectBegin()

	// Expect interface validation query (all interfaces exist)
	interfaceRows := sqlmock.NewRows([]string{"id"})
	for i := 1; i <= 128; i++ {
		interfaceRows.AddRow(i)
	}
	mock.ExpectQuery(`SELECT id FROM interface WHERE id = ANY\(\$1\)`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(interfaceRows)

	// Expect linked interfaces check (no interfaces linked)
	mock.ExpectQuery(`SELECT interface_id FROM`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"interface_id"}))

	// Expect 64 link insertions
	for i := 0; i < 64; i++ {
		mock.ExpectQuery(`INSERT INTO link`).
			WithArgs(int32(i*2+1), int32(i*2+2), float32(i)+0.5, "active").
			WillReturnRows(sqlmock.NewRows([]string{"id"}).AddRow(1000 + i))
	}

	// Expect commit
	mock.ExpectCommit()

	resp, err := service.BatchCreateLinks(ctx, req)

	require.NoError(t, err)
	assert.Equal(t, int32(64), resp.TotalRequested)
	assert.Equal(t, int32(64), resp.TotalCreated)
	assert.Len(t, resp.CreatedLinkIds, 64)
	assert.Empty(t, resp.FailedLinks)
	assert.Equal(t, "test-64-links", resp.RequestId)

	// Verify all expectations were met
	err = mock.ExpectationsWereMet()
	assert.NoError(t, err)
}

// TestBatchCreateLinksDatabaseError tests database error during transaction
func TestBatchCreateLinksDatabaseError(t *testing.T) {
	service, mock, cleanup := setupTestService(t)
	defer cleanup()

	ctx := context.Background()
	req := &pb.BatchCreateLinksRequest{
		Links: []*pb.LinkCreateSpec{
			{
				AInterfaceId: 1,
				BInterfaceId: 2,
				LengthKm:     1.0,
				Status:       "active",
			},
		},
		RequestId: "test-db-error",
	}

	// Expect transaction start
	mock.ExpectBegin()

	// Expect interface validation query to fail
	mock.ExpectQuery(`SELECT id FROM interface WHERE id = ANY\(\$1\)`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnError(sql.ErrConnDone)

	// Expect rollback
	mock.ExpectRollback()

	resp, err := service.BatchCreateLinks(ctx, req)

	require.Error(t, err)
	assert.Nil(t, resp)
	assert.Contains(t, err.Error(), "failed to validate interfaces")

	// Verify all expectations were met
	err = mock.ExpectationsWereMet()
	assert.NoError(t, err)
}

// TestBatchCreateLinksValidation tests validation errors (interface not found)
func TestBatchCreateLinksValidation(t *testing.T) {
	service, mock, cleanup := setupTestService(t)
	defer cleanup()

	ctx := context.Background()
	req := &pb.BatchCreateLinksRequest{
		Links: []*pb.LinkCreateSpec{
			{
				AInterfaceId: 1,
				BInterfaceId: 999, // Non-existent interface
				LengthKm:     1.0,
				Status:       "active",
			},
		},
		RequestId: "test-validation",
	}

	// Expect transaction start
	mock.ExpectBegin()

	// Expect interface validation query (only interface 1 exists)
	mock.ExpectQuery(`SELECT id FROM interface WHERE id = ANY\(\$1\)`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"id"}).AddRow(1))

	// Expect linked interfaces check
	mock.ExpectQuery(`SELECT interface_id FROM`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"interface_id"}))

	// Expect commit (no links created, but transaction should commit)
	mock.ExpectCommit()

	resp, err := service.BatchCreateLinks(ctx, req)

	require.NoError(t, err)
	assert.Equal(t, int32(1), resp.TotalRequested)
	assert.Equal(t, int32(0), resp.TotalCreated)
	assert.Empty(t, resp.CreatedLinkIds)
	assert.Len(t, resp.FailedLinks, 1)

	// Check failure details
	failure := resp.FailedLinks[0]
	assert.Equal(t, int32(0), failure.Index)
	assert.Equal(t, int32(1), failure.AInterfaceId)
	assert.Equal(t, int32(999), failure.BInterfaceId)
	assert.Equal(t, "INTERFACE_NOT_FOUND", failure.ErrorCode)
	assert.Contains(t, failure.ErrorMessage, "Interface B")
	assert.Contains(t, failure.ErrorMessage, "999")

	// Verify all expectations were met
	err = mock.ExpectationsWereMet()
	assert.NoError(t, err)
}

// TestBatchCreateLinksInterfaceAlreadyLinked tests interface already linked error
func TestBatchCreateLinksInterfaceAlreadyLinked(t *testing.T) {
	service, mock, cleanup := setupTestService(t)
	defer cleanup()

	ctx := context.Background()
	req := &pb.BatchCreateLinksRequest{
		Links: []*pb.LinkCreateSpec{
			{
				AInterfaceId: 1,
				BInterfaceId: 2,
				LengthKm:     1.0,
				Status:       "active",
			},
		},
		RequestId: "test-already-linked",
	}

	// Expect transaction start
	mock.ExpectBegin()

	// Expect interface validation query (both interfaces exist)
	mock.ExpectQuery(`SELECT id FROM interface WHERE id = ANY\(\$1\)`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"id"}).AddRow(1).AddRow(2))

	// Expect linked interfaces check (interface 1 is already linked)
	mock.ExpectQuery(`SELECT interface_id FROM`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"interface_id"}).AddRow(1))

	// Expect commit (no links created)
	mock.ExpectCommit()

	resp, err := service.BatchCreateLinks(ctx, req)

	require.NoError(t, err)
	assert.Equal(t, int32(1), resp.TotalRequested)
	assert.Equal(t, int32(0), resp.TotalCreated)
	assert.Empty(t, resp.CreatedLinkIds)
	assert.Len(t, resp.FailedLinks, 1)

	// Check failure details
	failure := resp.FailedLinks[0]
	assert.Equal(t, "INTERFACE_ALREADY_LINKED", failure.ErrorCode)
	assert.Contains(t, failure.ErrorMessage, "Interface A")
	assert.Contains(t, failure.ErrorMessage, "already linked")

	// Verify all expectations were met
	err = mock.ExpectationsWereMet()
	assert.NoError(t, err)
}

// TestBatchCreateLinksDryRun tests dry run mode (validation only)
func TestBatchCreateLinksDryRun(t *testing.T) {
	service, mock, cleanup := setupTestService(t)
	defer cleanup()

	ctx := context.Background()
	req := &pb.BatchCreateLinksRequest{
		Links: []*pb.LinkCreateSpec{
			{
				AInterfaceId: 1,
				BInterfaceId: 2,
				LengthKm:     1.0,
				Status:       "active",
			},
		},
		DryRun:    true,
		RequestId: "test-dry-run",
	}

	// Expect read-only transaction start
	mock.ExpectBegin()

	// Expect interface validation query
	mock.ExpectQuery(`SELECT id FROM interface WHERE id = ANY\(\$1\)`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"id"}).AddRow(1).AddRow(2))

	// Expect linked interfaces check
	mock.ExpectQuery(`SELECT interface_id FROM`).
		WithArgs(sqlmock.AnyArg()).
		WillReturnRows(sqlmock.NewRows([]string{"interface_id"}))

	// Expect rollback (read-only transaction)
	mock.ExpectRollback()

	resp, err := service.BatchCreateLinks(ctx, req)

	require.NoError(t, err)
	assert.Equal(t, int32(1), resp.TotalRequested)
	assert.Equal(t, int32(0), resp.TotalCreated) // Dry run: no links created
	assert.Empty(t, resp.CreatedLinkIds)
	assert.Empty(t, resp.FailedLinks)
	assert.Equal(t, "test-dry-run", resp.RequestId)

	// Verify all expectations were met
	err = mock.ExpectationsWereMet()
	assert.NoError(t, err)
}
