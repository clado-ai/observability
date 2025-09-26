"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import None from "@/components/none";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type {
  JsonEditorMode,
  JsonEditorProps,
  Property,
  PropertyType,
  SchemaObject,
  SchemaProperty,
} from "@/utils/types/component.types";

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

function convertValueToProperties(
  obj: Record<string, unknown> | null | undefined,
  parentId = "",
  mode: JsonEditorMode = "value",
): Property[] {
  if (!obj || typeof obj !== "object") return [];

  const properties: Property[] = [];

  for (const [key, value] of Object.entries(obj)) {
    // Handle temporary empty property keys
    let actualKey = key;
    let actualId = `${parentId}_${key}_${generateId()}`;

    if (key.startsWith("__empty_")) {
      actualKey = "";
      actualId = key.replace("__empty_", "");
    }

    const id = actualId;
    let type: PropertyType = "string";

    // In value mode (not schema), force everything to be string
    if (mode === "value") {
      type = "string";
    } else {
      // Schema mode - preserve original type detection
      if (typeof value === "number") {
        type = "number";
      } else if (typeof value === "boolean") {
        type = "boolean";
      } else if (value && typeof value === "object" && !Array.isArray(value)) {
        type = "object";
      } else if (typeof value === "string") {
        if (value.startsWith("data:image/")) {
          type = "image-base64";
        } else if (
          value.startsWith("http") &&
          /\.(jpg|jpeg|png|gif|webp)$/i.test(value)
        ) {
          type = "image-url";
        } else if (
          value.startsWith("blob:") &&
          /\.(jpg|jpeg|png|gif|webp)$/i.test(value)
        ) {
          type = "image-blob";
        } else {
          type = "string";
        }
      }
    }

    const property: Property = {
      id,
      key: actualKey,
      type,
      description: "",
      value: value,
    };

    if (
      type === "object" &&
      value &&
      typeof value === "object" &&
      mode === "schema"
    ) {
      property.children = convertValueToProperties(
        value as Record<string, unknown>,
        id,
        mode,
      );
    }

    properties.push(property);
  }

  return properties;
}

function convertSchemaToProperties(
  schema: SchemaObject | null | undefined,
  parentId = "",
): Property[] {
  if (!schema || typeof schema !== "object") return [];

  const properties: Property[] = [];

  for (const [key, schemaValue] of Object.entries(schema)) {
    // Handle temporary empty property keys
    let actualKey = key;
    let actualId = `${parentId}_${key}_${generateId()}`;

    if (key.startsWith("__empty_")) {
      actualKey = "";
      actualId = key.replace("__empty_", "");
    }

    const id = actualId;
    let type: PropertyType = "string";
    let description = "";

    // Handle schema objects with type and description
    if (
      schemaValue &&
      typeof schemaValue === "object" &&
      !Array.isArray(schemaValue)
    ) {
      const schemaObj = schemaValue as SchemaProperty;

      if (schemaObj.type) {
        switch (schemaObj.type) {
          case "string":
            type = "string";
            break;
          case "number":
          case "integer":
            type = "number";
            break;
          case "boolean":
            type = "boolean";
            break;
          case "object":
            type = "object";
            break;
          case "array":
            type = "array";
            break;
          case "image-base64":
            type = "image-base64";
            break;
          case "image-url":
            type = "image-url";
            break;
          default:
            type = "string";
        }
      }

      description = schemaObj.description || "";
    }

    const property: Property = {
      id,
      key: actualKey,
      type,
      description,
      required:
        schemaValue &&
        typeof schemaValue === "object" &&
        "required" in schemaValue
          ? schemaValue.required
          : false,
    };

    // Handle nested objects and arrays
    if (type === "object" && schemaValue && typeof schemaValue === "object") {
      const schemaObj = schemaValue as SchemaProperty;
      if (schemaObj.properties) {
        property.children = convertSchemaToProperties(schemaObj.properties, id);
      }
    } else if (
      type === "array" &&
      schemaValue &&
      typeof schemaValue === "object"
    ) {
      const schemaObj = schemaValue as SchemaProperty;
      if (schemaObj.items) {
        property.itemType = (schemaObj.items.type as PropertyType) || "string";
        property.itemDescription = schemaObj.items.description || "";
        // If the item type is object, convert the item schema to children
        if (property.itemType === "object" && schemaObj.items.properties) {
          property.children = convertSchemaToProperties(
            schemaObj.items.properties,
            id,
          );
        }
      }
    }

    properties.push(property);
  }

  return properties;
}

function convertPropertiesToSchema(properties: Property[]): SchemaObject {
  const result: SchemaObject = {};

  for (const property of properties) {
    if (!property.key.trim()) {
      // Keep empty properties in the schema to preserve UI state
      result[`__empty_${property.id}`] = {
        type: property.type,
        description: property.description,
        required: property.required,
      };
      continue;
    }

    if (property.type === "object" && property.children) {
      result[property.key] = {
        type: "object",
        description: property.description,
        required: property.required,
        properties: convertPropertiesToSchema(property.children),
      };
    } else if (property.type === "array") {
      const itemSchema: SchemaProperty = {
        type: property.itemType || "string",
        description: property.itemDescription || "",
      };

      // If array items are objects and we have children, add the properties
      if (property.itemType === "object" && property.children) {
        itemSchema.properties = convertPropertiesToSchema(property.children);
      }

      result[property.key] = {
        type: "array",
        description: property.description,
        required: property.required,
        items: itemSchema,
      };
    } else {
      result[property.key] = {
        type: property.type,
        description: property.description,
        required: property.required,
      };
    }
  }

  return result;
}

function convertPropertiesToValue(
  properties: Property[],
): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const property of properties) {
    if (!property.key.trim()) {
      // Keep empty properties in the value to preserve UI state
      result[`__empty_${property.id}`] = property.value;
      continue;
    }

    if (property.type === "object" && property.children) {
      result[property.key] = convertPropertiesToValue(property.children);
    } else {
      result[property.key] = property.value;
    }
  }

  return result;
}

function PropertyEditor({
  property,
  onUpdate,
  onDelete,
  depth = 0,
  mode = "schema",
}: {
  property: Property;
  onUpdate: (property: Property) => void;
  onDelete: () => void;
  depth?: number;
  mode?: JsonEditorMode;
}) {
  const handleKeyChange = (newKey: string) => {
    onUpdate({ ...property, key: newKey });
  };

  const handleTypeChange = (newType: PropertyType) => {
    // In value mode, only allow string type
    if (mode === "value" && newType !== "string") {
      return;
    }

    const updatedProperty: Property = {
      ...property,
      type: newType,
    };

    // Set default values for value mode
    if (mode === "value") {
      switch (newType) {
        case "number":
          updatedProperty.value = 0;
          break;
        case "boolean":
          updatedProperty.value = false;
          break;
        case "object":
          updatedProperty.value = {};
          break;
        default:
          updatedProperty.value = "";
          break;
      }
    }

    if (newType === "object") {
      updatedProperty.children = [];
      delete updatedProperty.itemType;
      delete updatedProperty.itemDescription;
    } else if (newType === "array") {
      updatedProperty.itemType = "string";
      updatedProperty.itemDescription = "";
      delete updatedProperty.children;
    } else {
      delete updatedProperty.children;
      delete updatedProperty.itemType;
      delete updatedProperty.itemDescription;
    }

    onUpdate(updatedProperty);
  };

  const handleValueChange = (newValue: unknown) => {
    onUpdate({ ...property, value: newValue });
  };

  const handleDescriptionChange = (newDescription: string) => {
    onUpdate({ ...property, description: newDescription });
  };

  const handleRequiredChange = (required: boolean) => {
    onUpdate({ ...property, required });
  };

  const handleItemTypeChange = (newItemType: PropertyType) => {
    const updatedProperty = { ...property, itemType: newItemType };

    if (newItemType === "object") {
      // Initialize with empty children for object schema definition
      updatedProperty.children = updatedProperty.children || [];
    } else {
      // Remove children if not object type
      delete updatedProperty.children;
    }

    onUpdate(updatedProperty);
  };

  const handleAddChildProperty = () => {
    if (
      property.type !== "object" &&
      !(property.type === "array" && property.itemType === "object")
    )
      return;

    const newProperty: Property = {
      id: generateId(),
      key: "",
      type: "string",
      description: "",
      ...(mode === "schema" && { required: false }),
      ...(mode === "value" && { value: "" }),
    };

    const updatedProperty = {
      ...property,
      children: [...(property.children || []), newProperty],
    };

    onUpdate(updatedProperty);
  };

  const handleUpdateChildProperty = (index: number, updatedChild: Property) => {
    if (!property.children) return;

    const newChildren = [...property.children];
    newChildren[index] = updatedChild;

    onUpdate({
      ...property,
      children: newChildren,
    });
  };

  const handleDeleteChildProperty = (index: number) => {
    if (!property.children) return;

    const newChildren = property.children.filter((_, i) => i !== index);

    onUpdate({
      ...property,
      children: newChildren,
    });
  };

  const renderValueEditor = () => {
    if (mode !== "value") return null;

    switch (property.type) {
      case "string":
      case "image-url":
        return (
          <Input
            value={property.value as string}
            onChange={(e) => handleValueChange(e.target.value)}
            placeholder={
              property.type === "image-url"
                ? "https://example.com/image.jpg"
                : "Enter property value..."
            }
          />
        );

      case "image-base64":
        return (
          <Textarea
            value={property.value as string}
            onChange={(e) => handleValueChange(e.target.value)}
            placeholder="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
            className="min-h-[80px] font-mono text-xs"
          />
        );

      case "number":
        return (
          <Input
            type="number"
            value={property.value as number}
            onChange={(e) => handleValueChange(Number(e.target.value) || 0)}
            placeholder="0"
          />
        );

      case "boolean":
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              checked={property.value as boolean}
              onCheckedChange={(checked) => handleValueChange(checked)}
            />
            <span className="text-sm">{property.value ? "True" : "False"}</span>
          </div>
        );

      default:
        return null;
    }
  };

  const renderArrayProperties = () => {
    if (property.type !== "array" || mode !== "schema") return null;

    return (
      <>
        <div className="space-y-2 bg-muted rounded-sm p-4">
          <div className="flex items-center gap-2">
            <Select
              value={property.itemType || "string"}
              onValueChange={handleItemTypeChange}
            >
              <SelectTrigger className="!h-[37px] w-32 bg-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="string">String</SelectItem>
                <SelectItem value="number">Number</SelectItem>
                <SelectItem value="boolean">Boolean</SelectItem>
                <SelectItem value="object">Object</SelectItem>
              </SelectContent>
            </Select>
            <Input
              value={property.itemDescription || ""}
              onChange={(e) =>
                onUpdate({ ...property, itemDescription: e.target.value })
              }
              placeholder="Description of array items"
            />
          </div>
        </div>

        {property.itemType === "object" && (
          <>
            <Button
              variant="ghost"
              onClick={handleAddChildProperty}
              className="w-full mb-0"
            >
              <i className="bx bx-plus"></i>
              Add Array Object Property <i className="bx bx-chevron-down"></i>
            </Button>
            {property.children && property.children.length > 0 && (
              <div className="pl-4 border-l-4 border-dotted mt-4">
                {property.children.map((child, index) => (
                  <PropertyEditor
                    key={child.id}
                    property={child}
                    onUpdate={(updatedChild) =>
                      handleUpdateChildProperty(index, updatedChild)
                    }
                    onDelete={() => handleDeleteChildProperty(index)}
                    depth={depth + 1}
                    mode={mode}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </>
    );
  };

  const renderNestedProperties = () => {
    if (property.type !== "object") return null;

    return (
      <>
        <Button
          variant="ghost"
          onClick={handleAddChildProperty}
          className="w-full mb-0"
        >
          <i className="bx bx-plus"></i>
          Add Nested Property <i className="bx bx-chevron-down"></i>
        </Button>
        {property.children && property.children.length > 0 && (
          <div className="pl-4 border-l-4 border-dotted mt-4">
            {property.children.map((child, index) => (
              <PropertyEditor
                key={child.id}
                property={child}
                onUpdate={(updatedChild) =>
                  handleUpdateChildProperty(index, updatedChild)
                }
                onDelete={() => handleDeleteChildProperty(index)}
                depth={depth + 1}
                mode={mode}
              />
            ))}
          </div>
        )}
      </>
    );
  };

  return (
    <div
      className={`propertyItem space-y-4 p-4 bg-white ${depth !== 0 ? "noConsiderRounded border rounded-md" : "considerRounded border-dotted"}`}
    >
      <div className="flex items-center gap-2">
        <div className="flex-1 flex flex-row items-center justify-start gap-4">
          <div>
            <Select value={property.type} onValueChange={handleTypeChange}>
              <SelectTrigger className="!h-[37px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="string">
                  <i className="bx bx-text"></i>
                  String
                </SelectItem>
                {mode === "schema" && (
                  <>
                    <SelectItem value="number">
                      <i className="bx bx-hash"></i>
                      Number
                    </SelectItem>
                    <SelectItem value="boolean">
                      <i className="bx bx-check-square"></i>
                      Boolean
                    </SelectItem>
                    <SelectItem value="object">
                      <i className="bx bx-code-curly"></i>
                      Object
                    </SelectItem>
                    <SelectItem value="array">
                      <i className="bx bx-list-ul"></i>
                      Array
                    </SelectItem>
                    <SelectItem value="image-base64">
                      <i className="bx bx-image"></i>
                      Image (Base64)
                    </SelectItem>
                    <SelectItem value="image-url">
                      <i className="bx bx-link"></i>
                      Image (URL)
                    </SelectItem>
                    <SelectItem value="image-blob">
                      <i className="bx bxs-file-image"></i>
                      Image (Blob)
                    </SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1">
            <Input
              value={property.key}
              onChange={(e) => handleKeyChange(e.target.value)}
              placeholder="Property name"
            />
          </div>
          {mode === "schema" && (
            <div className="flex items-center space-x-2">
              <Checkbox
                checked={property.required || false}
                onCheckedChange={(checked) =>
                  handleRequiredChange(checked as boolean)
                }
              />
              <span className="text-sm whitespace-nowrap">Required</span>
            </div>
          )}
          <Button
            variant="outline"
            size="icon"
            className="size-[38px]"
            onClick={onDelete}
          >
            <i className="bx bx-trash"></i>
          </Button>
        </div>
      </div>

      {mode === "schema" && (
        <Input
          value={property.description}
          onChange={(e) => handleDescriptionChange(e.target.value)}
          placeholder="Property description"
          className="text-sm"
        />
      )}

      {mode === "value" && renderValueEditor()}

      {renderArrayProperties()}

      {renderNestedProperties()}
    </div>
  );
}

export function JsonEditor({
  value,
  onChange,
  mode = "schema",
  className,
  onError,
}: JsonEditorProps) {
  const [properties, setProperties] = useState<Property[]>(() => {
    // Initialize properties based on mode
    try {
      if (value && typeof value === "object") {
        if (mode === "value") {
          return convertValueToProperties(
            value as Record<string, unknown>,
            "",
            mode,
          );
        } else {
          return convertSchemaToProperties(value as SchemaObject);
        }
      }
      return [];
    } catch {
      return [];
    }
  });
  const [error, setError] = useState<string | null>(null);
  const isInternalUpdate = useRef(false);

  // Initialize properties from prop value only when externally changed
  useEffect(() => {
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }

    try {
      if (value && typeof value === "object") {
        let newProperties: Property[];
        if (mode === "value") {
          newProperties = convertValueToProperties(
            value as Record<string, unknown>,
            "",
            mode,
          );
        } else {
          newProperties = convertSchemaToProperties(value as SchemaObject);
        }
        setProperties(newProperties);
      } else {
        setProperties([]);
      }
      setError(null);
      onError?.(null);
    } catch (e) {
      const errorMessage = `Failed to parse initial ${mode}: ${(e as Error).message}`;
      setError(errorMessage);
      onError?.(errorMessage);
    }
  }, [value, onError, mode]);

  // Helper to update parent component value
  const updateParentValue = useCallback(
    (newProperties: Property[]) => {
      try {
        let result: SchemaObject | Record<string, unknown>;
        if (mode === "value") {
          result = convertPropertiesToValue(newProperties);
        } else {
          result = convertPropertiesToSchema(newProperties);
        }
        isInternalUpdate.current = true;
        onChange(result);
        setError(null);
        onError?.(null);
      } catch (e) {
        const errorMessage = `Failed to convert properties to ${mode}: ${(e as Error).message}`;
        setError(errorMessage);
        onError?.(errorMessage);
      }
    },
    [onChange, onError, mode],
  );

  const handleAddProperty = () => {
    const newProperty: Property = {
      id: generateId(),
      key: "",
      type: "string",
      description: "",
      ...(mode === "schema" && { required: false }),
      ...(mode === "value" && { value: "" }),
    };

    const newProperties = [...properties, newProperty];
    setProperties(newProperties);
    updateParentValue(newProperties);
  };

  const handleUpdateProperty = (index: number, updatedProperty: Property) => {
    const newProperties = [...properties];
    newProperties[index] = updatedProperty;
    setProperties(newProperties);
    updateParentValue(newProperties);
  };

  const handleDeleteProperty = (index: number) => {
    const newProperties = properties.filter((_, i) => i !== index);
    setProperties(newProperties);
    updateParentValue(newProperties);
  };

  const handleUsePreset = (preset: SchemaObject | Record<string, unknown>) => {
    let newProperties: Property[];
    if (mode === "value") {
      newProperties = convertValueToProperties(
        preset as Record<string, unknown>,
        "",
        mode,
      );
    } else {
      newProperties = convertSchemaToProperties(preset as SchemaObject);
    }
    setProperties(newProperties);
    updateParentValue(newProperties);
  };

  return (
    <div className={cn("border rounded-md", className)}>
      <div
        className={`flex items-center justify-between p-4 border-b rounded-t-md ${mode === "schema" ? "bg-accent" : "bg-muted"}`}
      >
        <span className="text-sm font-medium">
          {mode === "schema" ? "Schema Editor" : "JSON Editor"}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleAddProperty}>
            <i className="bx bx-plus"></i>
            Add Property
          </Button>
          {mode === "value" && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">
                  Use Preset
                  <i className="bx bx-chevron-down"></i>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem
                  onClick={() =>
                    handleUsePreset({
                      Authorization: "Bearer <insert api token>",
                    })
                  }
                >
                  <i className="bx bxs-dog"></i> Bearer Auth
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    handleUsePreset({
                      "x-api-key": "<insert api key>",
                    })
                  }
                >
                  <i className="bx bxs-key"></i> X-API Key
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    handleUsePreset({
                      Authorization: "Basic <insert api token>",
                    })
                  }
                >
                  <i className="bx bxs-log-in-circle"></i> Basic Auth
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    handleUsePreset({
                      Authorization: "<insert authorization header>",
                    })
                  }
                >
                  <i className="bx bx-dots-horizontal-rounded"></i> Other
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      <div className="bg-white rounded-b-md">
        {properties.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            <i className="bx bx-code-curly text-2xl mb-2 block"></i>
            <None>
              {mode === "schema"
                ? "No schema properties defined yet."
                : "No properties added yet."}
            </None>
          </div>
        ) : (
          properties.map((property, index) => (
            <PropertyEditor
              key={property.id}
              property={property}
              onUpdate={(updatedProperty) =>
                handleUpdateProperty(index, updatedProperty)
              }
              onDelete={() => handleDeleteProperty(index)}
              mode={mode}
            />
          ))
        )}
      </div>

      {error && (
        <div className="text-sm text-destructive p-4 border-t bg-destructive/5">
          <i className="bx bx-error-circle mr-1"></i>
          {error}
        </div>
      )}
    </div>
  );
}
