from pathlib import Path
from matplotlib.image import imread, imsave
import random

def rgb2gray(rgb):
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
    return gray


class Img:

    def __init__(self, path):
        """
        Do not change the constructor implementation
        """
        self.path = Path(path)
        self.data = rgb2gray(imread(path)).tolist()

    def save_img(self):
        """
        Do not change the below implementation
        """
        new_path = self.path.with_name(self.path.stem + '_filtered' + self.path.suffix)
        imsave(new_path, self.data, cmap='gray')
        return new_path

    def blur(self, blur_level=16):
        """
        This method blurs the image by a blur level

        :param blur_level: Determines the level by which to blur the image
        :return None:
        """
        try:
            blur_level = int(abs(blur_level))
        except ValueError as e:
            raise ValueError("Blur level must be a positive, whole number.") from e

        height = len(self.data)
        width = len(self.data[0])
        filter_sum = blur_level ** 2

        result = []
        for i in range(height - blur_level + 1):
            row_result = []
            for j in range(width - blur_level + 1):
                sub_matrix = [row[j:j + blur_level] for row in self.data[i:i + blur_level]]
                average = sum(sum(sub_row) for sub_row in sub_matrix) // filter_sum
                row_result.append(average)
            result.append(row_result)

        self.data = result

    def contour(self):
        """
        This method applies a contour effect to the image by calculating the differences between neighboring pixels along each row of the image matrix.

        :return None:
        """
        for i, row in enumerate(self.data):
            res = []
            for j in range(1, len(row)):
                res.append(abs(row[j-1] - row[j]))

            self.data[i] = res

    def rotate_clockwise(self, mat):
        """
        This method takes in the image matrix and rotates it clockwise

        for [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]] the output will be

        [[10, 7, 4, 1], [11, 8, 5, 2], [12, 9, 6, 3]]

        :param mat: list of lists
        :return: list of lists - rotated matrix
        """
        # Transpose the matrix by using zip(*mat)
        transposed_mat = list(zip(*mat))

        # Reverse each row of the transposed mat
        rotated_mat = [list(row[::-1]) for row in transposed_mat]

        return rotated_mat

    def rotate_anti_clockwise(self, mat):
        """
        This method takes in the image matrix and rotates it anti-clockwise.

        for [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]] the output will be:

        [[3, 6, 9, 12], [2, 5, 8, 11], [1, 4, 7, 10]]
        """
        # First, transpose the matrix
        transposed_mat = list(zip(*mat))

        # Then reverse the order of columns in the transposed matrix
        rotated_mat = [list(row) for row in reversed(transposed_mat)]

        return rotated_mat

    def rotate(self, direction="clockwise", deg=90):
        """
        This method takes in a direction and degrees and rotates the image accordingly

        :param direction: string of either "clockwise" or "anti-clockwise" (default "clockwise")
        :param deg: integer of either 90 or 180 or 270 (default 90)
        :return None: sets the class property data
        """
        try:
            deg = int(abs(deg))
        except ValueError as e:
            raise ValueError("Degrees must be a positive, whole number and only 90, 180 or 270.") from e

        if deg not in [90, 180, 270]:
            raise ValueError("Degrees may only be 90, 180 or 270.")

        mat = self.data

        # Calculate the number of 90-degree rotations needed
        num_rotations = deg // 90

        for _ in range(num_rotations):
            if direction == "clockwise":
                mat = self.rotate_clockwise(mat)
            elif direction == "anti-clockwise":
                # For anticlockwise rotation, you could directly rotate 270 degrees clockwise
                # if the desired rotation is 270 anticlockwise, or just do it anticlockwise.
                mat = self.rotate_anti_clockwise(mat)

        self.data = mat


    def salt_n_pepper(self, noise_level=0.05):
        """
        Applies salt and pepper noise to a given grayscale image.

        :param self.data: A 2D list representing the grayscale image.
        :param noise_level: A float representing the proportion of the image pixels to be affected by noise.
        :return None: sets the class property data - A 2D list representing the image with salt and pepper noise applied.
        """
        try:
            noise_level = float(abs(noise_level))
        except ValueError as e:
            raise ValueError("Noise level must be a number and may be fractional.") from e

        image = self.data

        # Calculate the total number of pixels in the image
        total_pixels = len(image) * len(image[0])

        # Calculate the number of pixels to be affected by noise
        affected_pixels = int(total_pixels * noise_level)

        for _ in range(affected_pixels):
            # Randomly choose a pixel in the image
            row = random.randint(0, len(image) - 1)
            col = random.randint(0, len(image[0]) - 1)

            # Randomly decide whether to apply salt or pepper
            if random.random() < 0.5:
                # Apply salt (set pixel to white)
                image[row][col] = 255
            else:
                # Apply pepper (set pixel to black)
                image[row][col] = 0

        self.data = image

    def concat(self, other_img, direction="horizontal", sides="right-to-left"):
        """
        This method concatenates two images together horizontally or vertically (side by side).
        - Currently it is limited to concatenating only two images

        It checks the dimensions of both images to ensure they are compatible for concatenation and throws a RuntimeError exception if not.
        For horizontal concatenation it checks both images' height and for vertical concatenation it rotates both images by 90deg (1 time clockwise) first using the self.rotate_clockwise() method and then check the height.
        In addition the user is able to choose for horizontal to concat right to left or left to right of image1 and image2 respectively and for vertical to concatenate bottom to top or top to bottom of image1 and image2 respectively (this determines how the image has to be rotated prior to being concatenated)

        :param other_img: An instance of image
        :param direction: Determines whether to concatenate horizontal or vertical (default "horizontal")
        :param sides: based on the direction the user will be able to choose which sides of the images to concatenate (default "right-to-left")
        :return new_image: A new image instance
        """
        # First I ensure that the direction matches the sides chosen
        if direction == "vertical" and sides == "right-to-left":
            sides = "top-to-bottom"
        elif direction == "horizontal" and sides in ["top-to-bottom", "bottom-to-top"]:
            direction = "vertical"

        if (direction == "horizontal" and sides not in ["right-to-left", "left-to-right"]) or (direction == "vertical" and sides not in ["top-to-bottom", "bottom-to-top"]):
            raise ValueError("The sides you've chosen to concatenate don't match the direction chosen. Please refer to the 'help'.")
        elif sides not in ["right-to-left", "left-to-right", "top-to-bottom", "bottom-to-top"]:
            raise ValueError("The sides you've chosen to concatenate aren't of the allowed options. Please refer to the 'help'.")

        image1 = self.data
        image2 = other_img.data

        # Second, handle rotation if needed for vertical concatenation
        if direction == "vertical":
            image1 = self.rotate_clockwise(image1)
            image2 = self.rotate_clockwise(image2)

        # Check if the images are compatible for concatenation
        if len(image1) != len(image2):
            raise RuntimeError("Images are incompatible for concatenation due to difference in height.")

        # Concatenate based on direction and side
        if direction == "horizontal":
            if sides == "right-to-left":
                concatenated_image = [row1 + row2 for row1, row2 in zip(image1, image2)]
            elif sides == "left-to-right":
                concatenated_image = [row2 + row1 for row1, row2 in zip(image1, image2)]
        elif direction == "vertical":
            if sides == "top-to-bottom":
                concatenated_image = [row1 + row2 for row1, row2 in zip(image1, image2)]
            elif sides == "bottom-to-top":
                concatenated_image = [row2 + row1 for row1, row2 in zip(image1, image2)]

            # Rotate back to original orientation
            concatenated_image = self.rotate_anti_clockwise(concatenated_image)

        self.data = concatenated_image

    def segment(self):
        """
        Segments the image by setting pixels with intensity greater than 100 to white (255),
        and all others to black (0).

        :return None:
        """
        for i, row in enumerate(self.data):
            for j, pixel in enumerate(row):
                # Check the intensity of each pixel
                self.data[i][j] = 255 if pixel > 100 else 0
