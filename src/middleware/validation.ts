/**
 * Input validation middleware using express-validator and Zod
 */

import { Request, Response, NextFunction } from 'express';
import { body, query, param, validationResult } from 'express-validator';
import { z } from 'zod';
import { ElementType } from '../types';
import { config } from '../config';

/**
 * Handle validation errors
 */
export function handleValidationErrors(req: Request, res: Response, next: NextFunction): void {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    res.status(400).json({
      success: false,
      error: 'Validation failed',
      code: 'VALIDATION_ERROR',
      details: errors.array()
    });
    return;
  }
  next();
}

/**
 * Zod schema validation middleware
 */
export function validateSchema<T>(schema: z.ZodSchema<T>) {
  return (req: Request, res: Response, next: NextFunction): void => {
    try {
      const validated = schema.parse({
        body: req.body,
        query: req.query,
        params: req.params
      });
      
      // Replace request data with validated data
      req.body = validated.body || req.body;
      req.query = validated.query || req.query;
      req.params = validated.params || req.params;
      
      next();
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({
          success: false,
          error: 'Validation failed',
          code: 'VALIDATION_ERROR',
          details: error.errors.map(err => ({
            field: err.path.join('.'),
            message: err.message,
            value: err.input
          }))
        });
      } else {
        next(error);
      }
    }
  };
}

// Zod schemas for validation
export const ElementTypeSchema = z.enum([
  'rectangle', 'ellipse', 'diamond', 'text', 'line', 'arrow', 'draw', 
  'image', 'frame', 'embeddable', 'magicframe'
]);

export const CreateElementSchema = z.object({
  body: z.object({
    type: ElementTypeSchema,
    x: z.number().finite(),
    y: z.number().finite(),
    width: z.number().positive().optional(),
    height: z.number().positive().optional(),
    text: z.string().max(10000).optional(), // Prevent extremely large text
    strokeColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).optional(),
    backgroundColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).optional(),
    strokeWidth: z.number().min(0).max(20).optional(),
    opacity: z.number().min(0).max(100).optional(),
    roughness: z.number().min(0).max(2).optional(),
    fontSize: z.number().min(8).max(200).optional(),
    fontFamily: z.string().max(100).optional()
  }).refine(data => {
    // Validate coordinates are within reasonable bounds
    const maxCoordinate = 1000000; // 1 million pixels
    return Math.abs(data.x) <= maxCoordinate && Math.abs(data.y) <= maxCoordinate;
  }, {
    message: "Coordinates must be within reasonable bounds"
  })
});

export const UpdateElementSchema = z.object({
  params: z.object({
    id: z.string().uuid('Invalid element ID format')
  }),
  body: z.object({
    x: z.number().finite().optional(),
    y: z.number().finite().optional(),
    width: z.number().positive().optional(),
    height: z.number().positive().optional(),
    text: z.string().max(10000).optional(),
    strokeColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).optional(),
    backgroundColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).optional(),
    strokeWidth: z.number().min(0).max(20).optional(),
    opacity: z.number().min(0).max(100).optional(),
    roughness: z.number().min(0).max(2).optional(),
    fontSize: z.number().min(8).max(200).optional(),
    fontFamily: z.string().max(100).optional(),
    locked: z.boolean().optional()
  }).refine(data => {
    // Validate coordinates if provided
    const maxCoordinate = 1000000;
    if (data.x !== undefined && Math.abs(data.x) > maxCoordinate) return false;
    if (data.y !== undefined && Math.abs(data.y) > maxCoordinate) return false;
    return true;
  }, {
    message: "Coordinates must be within reasonable bounds"
  })
});

export const BatchCreateSchema = z.object({
  body: z.object({
    elements: z.array(CreateElementSchema.shape.body).max(100) // Limit batch size
  })
});

export const QueryElementsSchema = z.object({
  query: z.object({
    type: ElementTypeSchema.optional(),
    x: z.string().transform(val => parseFloat(val)).pipe(z.number().finite()).optional(),
    y: z.string().transform(val => parseFloat(val)).pipe(z.number().finite()).optional(),
    locked: z.string().transform(val => val === 'true').pipe(z.boolean()).optional(),
    limit: z.string().transform(val => parseInt(val, 10)).pipe(
      z.number().min(1).max(config.performance.queryResultLimit)
    ).optional(),
    offset: z.string().transform(val => parseInt(val, 10)).pipe(
      z.number().min(0)
    ).optional()
  }).strict() // Prevent additional query parameters
});

export const ElementActionSchema = z.object({
  body: z.object({
    elementIds: z.array(z.string().uuid()).min(1).max(100), // Limit selection size
    alignment: z.enum(['left', 'center', 'right', 'top', 'middle', 'bottom']).optional(),
    direction: z.enum(['horizontal', 'vertical']).optional()
  })
});

// Express-validator chains for backwards compatibility
export const validateCreateElement = [
  body('type').isIn(['rectangle', 'ellipse', 'diamond', 'text', 'line', 'arrow', 'draw', 'image', 'frame', 'embeddable', 'magicframe']),
  body('x').isNumeric().isFloat({ min: -1000000, max: 1000000 }),
  body('y').isNumeric().isFloat({ min: -1000000, max: 1000000 }),
  body('width').optional().isNumeric().isFloat({ min: 0 }),
  body('height').optional().isNumeric().isFloat({ min: 0 }),
  body('text').optional().isString().isLength({ max: 10000 }),
  body('strokeColor').optional().matches(/^#[0-9a-fA-F]{6}$/),
  body('backgroundColor').optional().matches(/^#[0-9a-fA-F]{6}$/),
  body('strokeWidth').optional().isNumeric().isFloat({ min: 0, max: 20 }),
  body('opacity').optional().isNumeric().isFloat({ min: 0, max: 100 }),
  body('roughness').optional().isNumeric().isFloat({ min: 0, max: 2 }),
  body('fontSize').optional().isNumeric().isFloat({ min: 8, max: 200 }),
  body('fontFamily').optional().isString().isLength({ max: 100 }),
  handleValidationErrors
];

export const validateUpdateElement = [
  param('id').isUUID(),
  body('x').optional().isNumeric().isFloat({ min: -1000000, max: 1000000 }),
  body('y').optional().isNumeric().isFloat({ min: -1000000, max: 1000000 }),
  body('width').optional().isNumeric().isFloat({ min: 0 }),
  body('height').optional().isNumeric().isFloat({ min: 0 }),
  body('text').optional().isString().isLength({ max: 10000 }),
  body('strokeColor').optional().matches(/^#[0-9a-fA-F]{6}$/),
  body('backgroundColor').optional().matches(/^#[0-9a-fA-F]{6}$/),
  body('strokeWidth').optional().isNumeric().isFloat({ min: 0, max: 20 }),
  body('opacity').optional().isNumeric().isFloat({ min: 0, max: 100 }),
  body('roughness').optional().isNumeric().isFloat({ min: 0, max: 2 }),
  body('fontSize').optional().isNumeric().isFloat({ min: 8, max: 200 }),
  body('fontFamily').optional().isString().isLength({ max: 100 }),
  body('locked').optional().isBoolean(),
  handleValidationErrors
];

export const validateElementId = [
  param('id').isUUID(),
  handleValidationErrors
];

export const validateQueryElements = [
  query('type').optional().isIn(['rectangle', 'ellipse', 'diamond', 'text', 'line', 'arrow', 'draw', 'image', 'frame', 'embeddable', 'magicframe']),
  query('x').optional().isNumeric(),
  query('y').optional().isNumeric(),
  query('locked').optional().isBoolean(),
  query('limit').optional().isInt({ min: 1, max: config.performance.queryResultLimit }),
  query('offset').optional().isInt({ min: 0 }),
  handleValidationErrors
];

export const validateElementAction = [
  body('elementIds').isArray({ min: 1, max: 100 }),
  body('elementIds.*').isUUID(),
  body('alignment').optional().isIn(['left', 'center', 'right', 'top', 'middle', 'bottom']),
  body('direction').optional().isIn(['horizontal', 'vertical']),
  handleValidationErrors
];

/**
 * Sanitize input to prevent XSS and injection attacks
 */
export function sanitizeInput(req: Request, res: Response, next: NextFunction): void {
  // Recursively sanitize object properties
  function sanitizeObject(obj: any): any {
    if (typeof obj === 'string') {
      // Remove potentially dangerous characters and patterns
      return obj
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
        .replace(/javascript:/gi, '') // Remove javascript: protocol
        .replace(/on\w+\s*=/gi, '') // Remove event handlers
        .trim();
    } else if (Array.isArray(obj)) {
      return obj.map(sanitizeObject);
    } else if (obj && typeof obj === 'object') {
      const sanitized: any = {};
      for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
          sanitized[key] = sanitizeObject(obj[key]);
        }
      }
      return sanitized;
    }
    return obj;
  }

  req.body = sanitizeObject(req.body);
  req.query = sanitizeObject(req.query);
  
  next();
}