import { Box, Icon, Input, Stack, Text, useColorModeValue } from '@chakra-ui/react';
import { useState } from 'react';
import type { ChangeEvent, DragEvent, ElementType } from 'react';

interface FileDropZoneProps {
  icon: ElementType;
  description: string;
  helper?: string;
  accept?: string;
  multiple?: boolean;
  onFilesSelected: (files: FileList) => void;
}

export const FileDropZone = ({ icon, description, helper, accept, multiple, onFilesSelected }: FileDropZoneProps) => {
  const borderColor = useColorModeValue('gray.200', 'rgba(255,255,255,0.18)');
  const hoverColor = useColorModeValue('purple.400', 'rgba(112,76,255,0.6)');
  const bg = useColorModeValue('white', 'rgba(16,14,32,0.75)');
  const [isDragging, setIsDragging] = useState(false);

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const target = event.target;
    if (target.files && target.files.length > 0) {
      onFilesSelected(target.files);
      // Reset the value so selecting the same file twice still triggers onChange
      target.value = '';
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    if (event.dataTransfer.files?.length) {
      onFilesSelected(event.dataTransfer.files);
    }
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
  };

  return (
    <Box
      borderWidth={2}
      borderStyle="dashed"
      borderColor={isDragging ? hoverColor : borderColor}
      borderRadius="2xl"
      p={6}
      textAlign="center"
      cursor="pointer"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      position="relative"
      transition="border-color 0.2s ease, transform 0.2s ease"
      bg={bg}
      boxShadow="0 12px 30px -18px rgba(112,76,255,0.45)"
      _hover={{ transform: 'translateY(-2px)' }}
    >
      <Stack spacing={2} align="center">
        <Icon as={icon} boxSize={8} color="purple.400" />
        <Text fontWeight="semibold">{description}</Text>
        {helper && (
          <Text fontSize="sm" color="gray.500">
            {helper}
          </Text>
        )}
        <Input
          type="file"
          accept={accept}
          multiple={multiple}
          position="absolute"
          inset={0}
          opacity={0}
          cursor="pointer"
          onChange={handleInputChange}
        />
      </Stack>
    </Box>
  );
};

export default FileDropZone;
