# Coding Standards & Best Practices
## Cricket Academy Management Platform

**Version:** 1.0  
**Date:** December 2024  
**Status:** Active

---

## 1. Executive Summary

This document defines coding standards, best practices, and guidelines for the Cricket Academy Management Platform. All code must follow these standards to ensure maintainability, readability, and seamless feature enhancements by future developers.

---

## 2. Core Principles

### 2.1 Code Quality Principles

1. **Readability First**: Code should be self-documenting with clear naming
2. **Comments for Why, Not What**: Explain business logic and complex decisions
3. **DRY (Don't Repeat Yourself)**: Avoid code duplication
4. **SOLID Principles**: Follow object-oriented design principles
5. **Consistent Structure**: Same patterns throughout the codebase
6. **Future-Proof**: Easy to extend and modify

---

## 3. Commenting Standards

### 3.1 Comment Types

#### 3.1.1 File Header Comments

Every file must start with a header comment explaining its purpose:

```typescript
/**
 * Performance Review API Routes
 * 
 * Handles all HTTP requests related to performance reviews including:
 * - Creating new reviews (coach only)
 * - Updating existing reviews
 * - Fetching reviews for players/coaches
 * - Submitting self-reviews (players)
 * 
 * Multi-tenancy: All routes automatically filter by academy_id from JWT token
 * Authorization: Coach can review any player in their academy, players can only view their own
 * 
 * @module routes/performance
 * @author Development Team
 * @since 1.0.0
 */
```

#### 3.1.2 Function/Method Comments

Every function must have a JSDoc comment:

```typescript
/**
 * Creates a new performance review for a player
 * 
 * Business Logic:
 * - Only coaches can create reviews
 * - Reviews are automatically scoped to coach's academy (multi-tenancy)
 * - If review for same player/date/category exists, it updates instead of creating new
 * - Automatically invalidates React Query cache for related queries
 * 
 * @param {Object} reviewData - Review data from request body
 * @param {string} reviewData.playerId - UUID of player being reviewed
 * @param {string} reviewData.reviewDate - Date of review (YYYY-MM-DD)
 * @param {string} reviewData.category - Performance category (batting/bowling/fielding/fitness)
 * @param {Object} reviewData.ratings - Object with metric ratings (1-10 scale)
 * @param {string} reviewData.coachNotes - Optional coach feedback text
 * @param {string[]} reviewData.strengths - Array of strength tags
 * @param {string[]} reviewData.focusAreas - Array of focus area tags
 * @param {Object} req - Express request object (contains user JWT token)
 * 
 * @returns {Promise<Object>} Created/updated review object
 * 
 * @throws {Error} 400 - Validation error (missing required fields)
 * @throws {Error} 403 - Forbidden (player not in coach's academy)
 * @throws {Error} 404 - Player not found
 * 
 * @example
 * // Coach reviews player's batting performance
 * const review = await createPerformanceReview({
 *   playerId: 'uuid-123',
 *   reviewDate: '2024-12-10',
 *   category: 'batting',
 *   ratings: { footwork: 8, timing: 9, selection: 7 },
 *   coachNotes: 'Excellent footwork today!',
 *   strengths: ['Weight Transfer'],
 *   focusAreas: ['Playing Spin']
 * }, req);
 */
async function createPerformanceReview(reviewData, req) {
  // Implementation
}
```

#### 3.1.3 Inline Comments

Use inline comments to explain **why**, not **what**:

```typescript
// ❌ BAD: Explains what the code does (obvious)
const total = a + b; // Adds a and b together

// ✅ GOOD: Explains why (business logic)
// Calculate average rating: Sum all metrics and divide by count
// We use 5 as default for missing metrics to avoid skewing averages
const averageRating = Object.values(ratings).reduce((sum, val) => sum + (val || 5), 0) / metricsCount;

// ❌ BAD: No comment for complex logic
const academyId = req.user.academyId || req.body.academyId;

// ✅ GOOD: Explains security decision
// CRITICAL: Always use academy_id from JWT token, never from request body
// This prevents cross-academy data access (security requirement)
const academyId = req.user.academyId;
if (req.body.academyId && req.body.academyId !== academyId) {
  throw new ForbiddenError('Cannot access data from different academy');
}
```

#### 3.1.4 Section Comments

Use section comments to organize complex functions:

```typescript
async function processFitnessAssessment(testData, req) {
  // ============================================
  // STEP 1: VALIDATION & AUTHORIZATION
  // ============================================
  // Validate test type exists in our test database
  // Check coach has permission to assess this player
  // Ensure player belongs to coach's academy (multi-tenancy check)
  
  // ============================================
  // STEP 2: CALCULATE SCORE & BENCHMARKS
  // ============================================
  // For Yo-Yo test: Convert level/shuttle to VO2 max estimate
  // For time-based tests: Compare against age-group benchmarks
  // Store raw score and calculated metrics separately
  
  // ============================================
  // STEP 3: SAVE TO DATABASE
  // ============================================
  // Use transaction to ensure data consistency
  // Update player's latest fitness score
  // Create assessment record with all metadata
  
  // ============================================
  // STEP 4: INVALIDATE CACHE & NOTIFY
  // ============================================
  // Invalidate React Query cache for player's fitness data
  // Send push notification to player about new assessment
  // Log assessment creation for analytics
}
```

---

## 4. Code Structure & Organization

### 4.1 File Organization

```
backend/
├── src/
│   ├── config/           # Configuration files
│   │   ├── database.ts
│   │   ├── redis.ts
│   │   └── env.ts
│   ├── middleware/       # Express middleware
│   │   ├── auth.ts       # JWT authentication
│   │   ├── academy.ts    # Academy context injection
│   │   └── errorHandler.ts
│   ├── routes/           # API route handlers
│   │   ├── auth/
│   │   ├── performance/
│   │   ├── roster/
│   │   └── fitness/
│   ├── services/         # Business logic
│   │   ├── reviewService.ts
│   │   ├── playerService.ts
│   │   └── sessionService.ts
│   ├── models/           # Database models (Prisma)
│   │   └── index.ts
│   ├── utils/            # Helper functions
│   │   ├── validators.ts
│   │   ├── formatters.ts
│   │   └── errors.ts
│   ├── types/            # TypeScript types
│   │   ├── api.ts
│   │   └── database.ts
│   └── __tests__/        # Test files
│       ├── routes/
│       └── services/

frontend/
├── src/
│   ├── screens/          # Screen components
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── reviews/
│   │   └── fitness/
│   ├── components/      # Reusable components
│   │   ├── common/       # Button, Card, Input
│   │   ├── forms/       # Form components
│   │   └── charts/      # Chart components
│   ├── services/        # API client
│   │   ├── api.ts
│   │   └── auth.ts
│   ├── hooks/           # Custom React hooks
│   │   ├── useAuth.ts
│   │   └── useReviews.ts
│   ├── utils/           # Helper functions
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── types/           # TypeScript types
│   │   └── index.ts
│   └── __tests__/       # Test files
```

### 4.2 Component Structure

Every component should follow this structure:

```typescript
/**
 * PerformanceReviewForm Component
 * 
 * Allows coaches to create/edit performance reviews for players.
 * Handles rating inputs, coach notes, and strength/focus area tags.
 * 
 * Features:
 * - Real-time rating updates with visual feedback
 * - Tag management (add/remove strengths and focus areas)
 * - Auto-save draft (saves to local storage every 30 seconds)
 * - Validation before submission
 * 
 * @component
 * @example
 * <PerformanceReviewForm
 *   playerId="uuid-123"
 *   initialData={existingReview}
 *   onSave={handleSave}
 *   onCancel={handleCancel}
 * />
 */

// ============================================
// IMPORTS
// ============================================
import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, Button } from 'react-native';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createReview, updateReview } from '../services/api';
import { validateRatings } from '../utils/validators';
import type { ReviewData, Player } from '../types';

// ============================================
// TYPES & INTERFACES
// ============================================
interface PerformanceReviewFormProps {
  playerId: string;
  initialData?: ReviewData;
  onSave?: (review: ReviewData) => void;
  onCancel?: () => void;
}

interface FormState {
  ratings: Record<string, number>;
  coachNotes: string;
  strengths: string[];
  focusAreas: string[];
}

// ============================================
// CONSTANTS
// ============================================
const DEFAULT_RATING = 5; // Default rating for unrated metrics
const AUTO_SAVE_INTERVAL = 30000; // 30 seconds

// ============================================
// COMPONENT
// ============================================
export const PerformanceReviewForm: React.FC<PerformanceReviewFormProps> = ({
  playerId,
  initialData,
  onSave,
  onCancel,
}) => {
  // ============================================
  // STATE MANAGEMENT
  // ============================================
  const [formState, setFormState] = useState<FormState>({
    ratings: initialData?.ratings || {},
    coachNotes: initialData?.coachNotes || '',
    strengths: initialData?.strengths || [],
    focusAreas: initialData?.focusAreas || [],
  });

  // ============================================
  // HOOKS
  // ============================================
  const queryClient = useQueryClient();
  
  const saveMutation = useMutation({
    mutationFn: (data: ReviewData) => 
      initialData ? updateReview(initialData.id, data) : createReview(data),
    onSuccess: () => {
      // Invalidate related queries to refresh UI
      queryClient.invalidateQueries(['reviews', playerId]);
      queryClient.invalidateQueries(['roster']);
      onSave?.(formState);
    },
  });

  // ============================================
  // EFFECTS
  // ============================================
  // Auto-save draft to local storage
  useEffect(() => {
    const interval = setInterval(() => {
      localStorage.setItem(`review-draft-${playerId}`, JSON.stringify(formState));
    }, AUTO_SAVE_INTERVAL);

    return () => clearInterval(interval);
  }, [formState, playerId]);

  // ============================================
  // EVENT HANDLERS
  // ============================================
  const handleRatingChange = useCallback((metric: string, value: number) => {
    setFormState(prev => ({
      ...prev,
      ratings: { ...prev.ratings, [metric]: value },
    }));
  }, []);

  const handleSubmit = useCallback(async () => {
    // Validate before submission
    const validation = validateRatings(formState.ratings);
    if (!validation.isValid) {
      alert(validation.error);
      return;
    }

    await saveMutation.mutateAsync({
      playerId,
      ...formState,
    });
  }, [formState, playerId, saveMutation]);

  // ============================================
  // RENDER
  // ============================================
  return (
    <View>
      {/* Component JSX */}
    </View>
  );
};
```

---

## 5. Naming Conventions

### 5.1 Variables & Functions

```typescript
// ✅ GOOD: Descriptive, camelCase
const playerAttendancePercentage = calculateAttendance(playerId);
const isCoachView = userRole === 'coach';
const hasPendingReviews = reviews.filter(r => r.status === 'pending').length > 0;

// ❌ BAD: Abbreviations, unclear names
const pct = calc(playerId);
const cv = role === 'c';
const hpr = reviews.filter(r => r.s === 'p').length > 0;

// ✅ GOOD: Boolean variables start with is/has/should
const isAuthenticated = !!token;
const hasPermission = checkPermission(user, action);
const shouldShowModal = condition && !isLoading;

// ✅ GOOD: Functions are verbs
function calculateAverageRating(ratings: number[]): number { }
function validateReviewData(data: ReviewData): ValidationResult { }
function formatDate(date: Date): string { }
```

### 5.2 Components

```typescript
// ✅ GOOD: PascalCase, descriptive
export const PerformanceReviewForm = () => { };
export const PlayerDashboard = () => { };
export const FitnessAssessmentCard = () => { };

// ❌ BAD: Unclear, abbreviations
export const PRForm = () => { };
export const PDash = () => { };
export const FACard = () => { };
```

### 5.3 Constants

```typescript
// ✅ GOOD: UPPER_SNAKE_CASE for constants
const MAX_RATING_VALUE = 10;
const MIN_RATING_VALUE = 1;
const DEFAULT_ACADEMY_CODE_PREFIX = 'ACD-';
const API_BASE_URL = process.env.VITE_API_BASE_URL;

// ✅ GOOD: camelCase for configuration objects
const apiConfig = {
  baseUrl: process.env.VITE_API_BASE_URL,
  timeout: 5000,
  retryAttempts: 3,
};
```

### 5.4 Files & Folders

```
// ✅ GOOD: kebab-case for files
performance-review-form.tsx
player-dashboard.tsx
review-service.ts

// ✅ GOOD: camelCase for folders
performanceReviews/
playerDashboard/
reviewService/
```

---

## 6. Best Practices

### 6.1 Avoid Code Duplication (DRY)

```typescript
// ❌ BAD: Duplicated validation logic
function createReview(data) {
  if (!data.playerId) throw new Error('Player ID required');
  if (!data.ratings) throw new Error('Ratings required');
  if (!data.category) throw new Error('Category required');
  // ... create logic
}

function updateReview(id, data) {
  if (!data.playerId) throw new Error('Player ID required');
  if (!data.ratings) throw new Error('Ratings required');
  if (!data.category) throw new Error('Category required');
  // ... update logic
}

// ✅ GOOD: Extract to reusable function
/**
 * Validates review data before create/update operations
 * 
 * @param {ReviewData} data - Review data to validate
 * @throws {ValidationError} If validation fails
 */
function validateReviewData(data: ReviewData): void {
  const requiredFields = ['playerId', 'ratings', 'category'];
  const missingFields = requiredFields.filter(field => !data[field]);
  
  if (missingFields.length > 0) {
    throw new ValidationError(`Missing required fields: ${missingFields.join(', ')}`);
  }
  
  // Validate ratings are within range
  Object.values(data.ratings).forEach(rating => {
    if (rating < 1 || rating > 10) {
      throw new ValidationError('Ratings must be between 1 and 10');
    }
  });
}

function createReview(data) {
  validateReviewData(data); // Reuse validation
  // ... create logic
}

function updateReview(id, data) {
  validateReviewData(data); // Reuse validation
  // ... update logic
}
```

### 6.2 Error Handling

```typescript
// ❌ BAD: Generic error handling
try {
  await saveReview(data);
} catch (error) {
  console.log(error);
  alert('Error occurred');
}

// ✅ GOOD: Specific error handling with user-friendly messages
try {
  await saveReview(data);
  showSuccessToast('Review saved successfully');
} catch (error) {
  // Log full error for debugging
  console.error('Failed to save review:', {
    error,
    data,
    userId: req.user.id,
    timestamp: new Date().toISOString(),
  });

  // Show user-friendly message based on error type
  if (error instanceof ValidationError) {
    showErrorToast(`Validation error: ${error.message}`);
  } else if (error instanceof NetworkError) {
    showErrorToast('Network error. Please check your connection.');
    // Queue for retry when online
    queueForRetry('saveReview', data);
  } else if (error.status === 403) {
    showErrorToast('You do not have permission to perform this action.');
  } else {
    showErrorToast('An unexpected error occurred. Please try again.');
  }
}
```

### 6.3 TypeScript Usage

```typescript
// ❌ BAD: Using 'any' type
function processData(data: any): any {
  return data.something;
}

// ✅ GOOD: Proper typing
interface ReviewData {
  playerId: string;
  reviewDate: string;
  category: 'batting' | 'bowling' | 'fielding' | 'fitness';
  ratings: Record<string, number>;
  coachNotes?: string; // Optional field
  strengths?: string[];
  focusAreas?: string[];
}

function processReviewData(data: ReviewData): ProcessedReview {
  // TypeScript will catch errors at compile time
  return {
    ...data,
    averageRating: calculateAverage(data.ratings),
  };
}
```

### 6.4 Async/Await vs Promises

```typescript
// ❌ BAD: Promise chains (harder to read)
function loadPlayerData(playerId) {
  return fetchPlayer(playerId)
    .then(player => {
      return fetchReviews(playerId)
        .then(reviews => {
          return fetchGoals(playerId)
            .then(goals => {
              return { player, reviews, goals };
            });
        });
    })
    .catch(error => {
      console.error(error);
    });
}

// ✅ GOOD: Async/await (cleaner, easier to read)
/**
 * Loads all data for a player (profile, reviews, goals)
 * 
 * @param {string} playerId - UUID of player
 * @returns {Promise<PlayerData>} Combined player data
 */
async function loadPlayerData(playerId: string): Promise<PlayerData> {
  try {
    // Load data in parallel for better performance
    const [player, reviews, goals] = await Promise.all([
      fetchPlayer(playerId),
      fetchReviews(playerId),
      fetchGoals(playerId),
    ]);

    return { player, reviews, goals };
  } catch (error) {
    console.error('Failed to load player data:', error);
    throw new DataLoadError('Unable to load player data', { playerId, error });
  }
}
```

### 6.5 Component Props & State

```typescript
// ❌ BAD: Too many props, unclear structure
<ReviewForm
  playerId="123"
  coachId="456"
  date="2024-12-10"
  category="batting"
  ratings={{}}
  notes=""
  strengths={[]}
  focusAreas={[]}
  onSave={handleSave}
  onCancel={handleCancel}
  onUpdate={handleUpdate}
/>

// ✅ GOOD: Grouped props, clear structure
interface ReviewFormProps {
  // Core data
  review: ReviewData;
  player: Player;
  
  // Callbacks (grouped by purpose)
  callbacks: {
    onSave: (data: ReviewData) => void;
    onCancel: () => void;
    onUpdate?: (data: Partial<ReviewData>) => void;
  };
  
  // Optional configuration
  options?: {
    allowEdit?: boolean;
    showHistory?: boolean;
    autoSave?: boolean;
  };
}

<ReviewForm
  review={reviewData}
  player={player}
  callbacks={{
    onSave: handleSave,
    onCancel: handleCancel,
    onUpdate: handleUpdate,
  }}
  options={{
    allowEdit: true,
    autoSave: true,
  }}
/>
```

---

## 7. Multi-Tenancy Patterns

### 7.1 Academy Context Injection

```typescript
/**
 * Middleware to inject academy context into all requests
 * 
 * CRITICAL SECURITY: This ensures all database queries are automatically
 * scoped to the user's academy, preventing cross-academy data access.
 * 
 * How it works:
 * 1. Extract academy_id from JWT token (set during login)
 * 2. Attach to request object for use in route handlers
 * 3. All service functions must use this academy_id
 * 
 * @middleware
 */
export const academyContextMiddleware = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
) => {
  try {
    // Academy ID is set in JWT token during authentication
    // This is the ONLY source of truth for academy context
    const academyId = req.user.academyId;

    if (!academyId) {
      throw new UnauthorizedError('Academy context missing from token');
    }

    // Attach to request for use in route handlers and services
    req.academyId = academyId;

    // Set in Prisma context for automatic filtering (if using Prisma middleware)
    // This ensures ALL queries are automatically filtered by academy_id
    prisma.$use(async (params, next) => {
      if (params.model && params.action !== 'create') {
        params.args.where = {
          ...params.args.where,
          academy_id: academyId, // Automatic filtering
        };
      }
      return next(params);
    });

    next();
  } catch (error) {
    next(error);
  }
};
```

### 7.2 Service Layer Pattern

```typescript
/**
 * Performance Review Service
 * 
 * Business Logic Layer: Contains all business rules and data operations
 * for performance reviews. All database access goes through this service.
 * 
 * Multi-Tenancy: All operations automatically scoped to academy_id
 * 
 * @service
 */
class PerformanceReviewService {
  /**
   * Creates a new performance review
   * 
   * Business Rules:
   * 1. Only coaches can create reviews
   * 2. Player must belong to coach's academy (enforced by middleware)
   * 3. If review exists for same player/date/category, update instead
   * 4. Automatically calculate average rating
   * 
   * @param {ReviewData} data - Review data
   * @param {string} academyId - Academy ID from request context
   * @param {string} coachId - Coach ID from JWT token
   * @returns {Promise<Review>} Created review
   */
  async createReview(
    data: ReviewData,
    academyId: string,
    coachId: string
  ): Promise<Review> {
    // Validate player belongs to academy (double-check security)
    const player = await this.playerService.getPlayerById(
      data.playerId,
      academyId // Enforces academy isolation
    );

    if (!player) {
      throw new NotFoundError('Player not found in your academy');
    }

    // Check if review already exists (update instead of create)
    const existingReview = await prisma.performanceReview.findFirst({
      where: {
        player_id: data.playerId,
        review_date: data.reviewDate,
        category: data.category,
        academy_id: academyId, // CRITICAL: Always include academy_id
      },
    });

    if (existingReview) {
      // Update existing review instead of creating duplicate
      return this.updateReview(existingReview.id, data, academyId, coachId);
    }

    // Calculate average rating for quick display
    const averageRating = this.calculateAverageRating(data.ratings);

    // Create new review
    const review = await prisma.performanceReview.create({
      data: {
        ...data,
        academy_id: academyId, // CRITICAL: Always set academy_id
        coach_id: coachId,
        average_rating: averageRating,
      },
    });

    return review;
  }

  /**
   * Helper: Calculate average rating from ratings object
   * 
   * @private
   */
  private calculateAverageRating(ratings: Record<string, number>): number {
    const values = Object.values(ratings);
    if (values.length === 0) return 0;
    return values.reduce((sum, val) => sum + val, 0) / values.length;
  }
}
```

---

## 8. Testing Standards

### 8.1 Test File Structure

```typescript
/**
 * Performance Review Service Tests
 * 
 * Tests all business logic for performance reviews including:
 * - Creating reviews
 * - Updating reviews
 * - Academy isolation (security)
 * - Validation
 * 
 * @suite performanceReviewService
 */

import { PerformanceReviewService } from '../services/reviewService';
import { NotFoundError, ForbiddenError } from '../utils/errors';

describe('PerformanceReviewService', () => {
  let service: PerformanceReviewService;
  let mockAcademyId: string;
  let mockCoachId: string;

  beforeEach(() => {
    service = new PerformanceReviewService();
    mockAcademyId = 'academy-uuid-1';
    mockCoachId = 'coach-uuid-1';
  });

  describe('createReview', () => {
    it('should create a new review with valid data', async () => {
      // Arrange: Set up test data
      const reviewData = {
        playerId: 'player-uuid-1',
        reviewDate: '2024-12-10',
        category: 'batting' as const,
        ratings: { footwork: 8, timing: 9 },
        coachNotes: 'Great session!',
      };

      // Act: Execute the function
      const result = await service.createReview(
        reviewData,
        mockAcademyId,
        mockCoachId
      );

      // Assert: Verify the result
      expect(result).toBeDefined();
      expect(result.player_id).toBe(reviewData.playerId);
      expect(result.academy_id).toBe(mockAcademyId); // Multi-tenancy check
      expect(result.coach_id).toBe(mockCoachId);
    });

    it('should enforce academy isolation', async () => {
      // Arrange: Try to create review for player from different academy
      const reviewData = {
        playerId: 'player-from-different-academy',
        // ... other data
      };

      // Act & Assert: Should throw ForbiddenError
      await expect(
        service.createReview(reviewData, mockAcademyId, mockCoachId)
      ).rejects.toThrow(ForbiddenError);
    });

    it('should update existing review instead of creating duplicate', async () => {
      // Test update logic
    });
  });
});
```

---

## 9. Documentation Requirements

### 9.1 README Files

Every major directory should have a README:

```markdown
# Performance Review Module

## Overview
This module handles all performance review functionality including creating, updating, and viewing reviews.

## Structure
- `routes/` - API endpoints
- `services/` - Business logic
- `components/` - UI components
- `__tests__/` - Test files

## Key Features
- Multi-academy isolation
- Real-time updates
- Auto-save drafts

## Usage Example
\`\`\`typescript
import { createReview } from './services/reviewService';

const review = await createReview(data, academyId, coachId);
\`\`\`

## Future Enhancements
- [ ] Bulk review creation
- [ ] Review templates
- [ ] Export to PDF
```

### 9.2 Code Examples in Comments

```typescript
/**
 * Calculates player's average performance rating across all categories
 * 
 * @example
 * // Calculate average for player with multiple category reviews
 * const playerId = 'uuid-123';
 * const average = await calculatePlayerAverage(playerId);
 * // Returns: { batting: 7.5, bowling: 6.8, fielding: 8.2, overall: 7.5 }
 * 
 * @example
 * // Handle player with no reviews
 * const average = await calculatePlayerAverage('new-player-uuid');
 * // Returns: { batting: 0, bowling: 0, fielding: 0, overall: 0 }
 */
```

---

## 10. Code Review Checklist

Before submitting code, ensure:

- [ ] All functions have JSDoc comments
- [ ] Complex logic has inline comments explaining "why"
- [ ] No code duplication (DRY principle)
- [ ] Proper error handling with user-friendly messages
- [ ] TypeScript types are used (no `any` types)
- [ ] Multi-tenancy is enforced (academy_id in all queries)
- [ ] Tests are written and passing
- [ ] Code follows naming conventions
- [ ] File structure is organized
- [ ] No console.log statements (use proper logging)

---

## 11. Common Patterns

### 11.1 API Route Pattern

```typescript
/**
 * Performance Review Routes
 * 
 * All routes are protected by authentication middleware
 * Academy context is automatically injected by academyContextMiddleware
 */
router.post(
  '/reviews',
  authenticate, // Verify JWT token
  academyContextMiddleware, // Inject academy_id
  validateReviewData, // Validate request body
  async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    try {
      // Business logic in service layer (not in route handler)
      const review = await reviewService.createReview(
        req.body,
        req.academyId, // From middleware
        req.user.id // From JWT token
      );

      res.status(201).json({
        success: true,
        data: { review },
      });
    } catch (error) {
      // Error handling middleware will catch this
      next(error);
    }
  }
);
```

### 11.2 React Component Pattern

```typescript
/**
 * Reusable component pattern with proper TypeScript and error handling
 */
interface ComponentProps {
  // Props definition
}

export const Component: React.FC<ComponentProps> = (props) => {
  // 1. Hooks at the top
  const [state, setState] = useState();
  const queryClient = useQueryClient();

  // 2. Derived state
  const computedValue = useMemo(() => {
    // Expensive computation
  }, [dependencies]);

  // 3. Effects
  useEffect(() => {
    // Side effects
    return () => {
      // Cleanup
    };
  }, [dependencies]);

  // 4. Event handlers
  const handleAction = useCallback(() => {
    // Handler logic
  }, [dependencies]);

  // 5. Render
  return (
    // JSX
  );
};
```

---

## 12. Anti-Patterns to Avoid

### 12.1 ❌ Don't Do This

```typescript
// ❌ Magic numbers without explanation
if (rating > 7) { }

// ❌ Unclear variable names
const d = new Date();
const u = getUser();

// ❌ No error handling
const data = await fetchData();

// ❌ Hardcoded values
if (academyId === '123') { }

// ❌ Commented out code
// const oldCode = something();

// ❌ Too many responsibilities in one function
function doEverything() {
  // 200 lines of code doing multiple things
}
```

### 12.2 ✅ Do This Instead

```typescript
// ✅ Named constants with explanation
const MINIMUM_GOOD_RATING = 7; // Ratings above 7 are considered "good"
if (rating > MINIMUM_GOOD_RATING) { }

// ✅ Descriptive variable names
const currentDate = new Date();
const currentUser = getUser();

// ✅ Proper error handling
try {
  const data = await fetchData();
} catch (error) {
  handleError(error);
}

// ✅ Configuration constants
const TEST_ACADEMY_ID = process.env.TEST_ACADEMY_ID;
if (academyId === TEST_ACADEMY_ID) { }

// ✅ Remove commented code, use version control instead
// (Git history shows old code)

// ✅ Single responsibility functions
function validateReviewData(data) { }
function saveReviewToDatabase(data) { }
function notifyPlayerAboutReview(review) { }
```

---

## 13. Summary

### Key Takeaways

1. **Comments**: Explain "why", not "what"
2. **Structure**: Consistent file and component organization
3. **Naming**: Descriptive, self-documenting names
4. **DRY**: No code duplication
5. **Types**: Use TypeScript properly
6. **Errors**: Handle errors gracefully
7. **Tests**: Write tests for all features
8. **Multi-Tenancy**: Always enforce academy isolation
9. **Documentation**: README files for major modules
10. **Review**: Follow checklist before submitting

### Remember

> **"Code is read 10x more often than it's written. Write for the next developer who will maintain your code."**

---

**Document Status**: Active - All developers must follow these standards

