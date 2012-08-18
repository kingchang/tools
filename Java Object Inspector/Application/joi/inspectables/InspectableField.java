package joi.inspectables;


import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.List;

import joi.Inspectable;
import joi.Writeable;
import joi.exceptions.InspectionDeniedException;
import joi.exceptions.InstanceFieldException;
import joi.exceptions.NullInspectionException;
import joi.exceptions.NullValueException;
import joi.exceptions.PrimitiveInspectionException;
import joi.values.java.lang.ClassValue;
import joi.values.java.lang.ObjectValue;


/**
 * A field that can be inspected.
 */
public class InspectableField implements Inspectable, Writeable {
    private Field _field;
    private Object _owner;
    private ObjectValue _inspectableValue;
    

    /**
     * Creates a field that can be inspected.
     * 
     * @param field field to be inspected
     * @param owner field owner (may be null for static fields)
     */
    public InspectableField(Field field, Object owner) {
        _field = field;
        _owner = owner;
        
        _field.setAccessible(true);
        _inspectableValue = ObjectValue.detectFromClass(field.getType());
    }
    

    public String describe() {
        String modifiers = Modifier.toString(getField().getModifiers());
        String value;
        
        try {
            value = getValueToOutput();
        }
        catch (InspectionDeniedException error) {
            value = "?";
        }
        catch (InstanceFieldException error) {
            value = null;
        }
        
        String description = String.format("%s%s%s %s",
            modifiers,
            (modifiers.length() > 0 ? " " : ""),
            ClassValue.getClassNameOf(getField().getType()),
            getField().getName());
        
        return description + (value == null ? "" : " = " + value);
    }
    

    public Object getValue() {
        try {
            return getField().get(_owner);
        }
        catch (IllegalAccessException exception) {
            throw new InspectionDeniedException();
        }
        catch (NullPointerException exception) {
            throw new InstanceFieldException();
        }
    }
    

    public String getValueToOutput() {
        _inspectableValue.setValue(getValue());
        return _inspectableValue.getValueToOutput();
    }
    

    public List<Inspectable> inspect() {
        Object value = getValue();
        
        if (value == null) {
            throw new NullInspectionException();
        }
        
        if (getField().getType().isPrimitive()) {
            throw new PrimitiveInspectionException();
        }
        
        _inspectableValue.setValue(value);
        return _inspectableValue.inspect();
    }
    

    public void setValue(Object value) {
        if (getField().getType().isPrimitive() && (value == null)) {
            throw new NullValueException();
        }
        
        try {
            getField().set(_owner, value);
        }
        catch (IllegalAccessException exception) {
            throw new InspectionDeniedException();
        }
        catch (NullPointerException exception) {
            throw new InstanceFieldException();
        }
    }
    

    public void setValueFromInput(String input) {
        _inspectableValue.setValueFromInput(input);
        setValue(_inspectableValue.getValue());
    }
    

    /**
     * Gets the field.
     * 
     * @return the underlying field
     */
    protected Field getField() {
        return _field;
    }
}
