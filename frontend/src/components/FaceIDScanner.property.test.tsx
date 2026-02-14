/**
 * Property-Based Tests for FaceIDScanner Component
 * 
 * Tests universal properties that should hold across all valid inputs.
 * Uses fast-check for property-based testing.
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { render, screen } from '@testing-library/react';
import FaceIDScanner from './FaceIDScanner';

describe('FaceIDScanner Property-Based Tests', () => {
  /**
   * Property 16: Score display formatting
   * 
   * For any score value received (0.0 to 1.0), the displayed percentage 
   * should equal Math.round(score * 100).
   * 
   * **Validates: Requirements 6.4**
   */
  it('Property 16: Score display formatting - displayed percentage equals Math.round(score * 100)', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary score values between 0.0 and 1.0
        fc.double({ min: 0.0, max: 1.0, noNaN: true }),
        fc.double({ min: 0.0, max: 1.0, noNaN: true }),
        fc.double({ min: 0.0, max: 1.0, noNaN: true }),

        async (livenessScore, emotionScore, deepfakeScore) => {
          // Render component with generated scores
          const { container } = render(
            <FaceIDScanner
              isScanning={true}
              progress={50}
              status="scanning"
              scores={{
                liveness: livenessScore,
                emotion: emotionScore,
                deepfake: deepfakeScore,
              }}
            />
          );

          // Calculate expected percentages using the same formula as the component
          const expectedLiveness = Math.round(livenessScore * 100);
          const expectedEmotion = Math.round(emotionScore * 100);
          const expectedDeepfake = Math.round(deepfakeScore * 100);

          // Verify liveness score display
          const livenessText = `${expectedLiveness}%`;
          const livenessElements = screen.getAllByText(livenessText);
          expect(livenessElements.length).toBeGreaterThan(0);

          // Verify emotion score display
          const emotionText = `${expectedEmotion}%`;
          const emotionElements = screen.getAllByText(emotionText);
          expect(emotionElements.length).toBeGreaterThan(0);

          // Verify deepfake score display
          const deepfakeText = `${expectedDeepfake}%`;
          const deepfakeElements = screen.getAllByText(deepfakeText);
          expect(deepfakeElements.length).toBeGreaterThan(0);

          // Verify the progress bar widths are set correctly (as percentages)
          // Note: We check that the text percentages match the expected formula
          // The progress bars use the raw score * 100 for width, which is tested
          // by verifying the component renders without errors and displays correct text
        }
      ),
      { numRuns: 15 } // Use 10-15 iterations for faster execution as requested
    );
  });
});
