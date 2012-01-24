#
# Jasy - Web Tooling Framework
# Copyright 2010-2012 Sebastian Werner
#

from jasy.js.util import *
import logging, json, msgpack
from jasy.js.output.Compressor import Compressor

# Shared instance
compressor = Compressor()

__all__ = ["ApiData"]

class ApiData():
    

    __slots__ = ["main", "constructor", "statics", "properties", "events", "members", "id", "uses"]

    
    def __init__(self, tree, id):
        
        self.id = id
        self.main = {}
        
        
        #
        # Export relevant usage data from scope scanner
        #
        self.uses = {}
        self.uses.update(tree.scope.shared)
        self.uses.update(tree.scope.packages)


        #
        # core.Module
        #
        coreModule = findCall(tree, "core.Module")
        if coreModule:
            self.setMain("core.Module", coreModule.parent)
            
            staticsMap = getParameterFromCall(coreModule, 1)
            if staticsMap:
                self.statics = {}
                for staticsEntry in staticsMap:
                    self.addEntry(staticsEntry[0].value, staticsEntry[1], staticsEntry, self.statics)


        #
        # core.Interface
        #
        coreInterface = findCall(tree, "core.Interface")
        if coreInterface:
            self.setMain("core.Interface", coreInterface.parent)
            
            configMap = getParameterFromCall(coreInterface, 1)
            if configMap:
                for propertyInit in configMap:
                    
                    sectionName = propertyInit[0].value
                    sectionValue = propertyInit[1]
                    
                    if sectionName == "properties":
                        self.properties = {}
                        for propertyEntry in sectionValue:
                            self.addProperty(propertyEntry[0].value, propertyEntry[1], propertyEntry, self.properties)
                    
                    elif sectionName == "events":
                        self.events = {}
                        for eventEntry in sectionValue:
                            self.addEvent(eventEntry[0].value, eventEntry[1], eventEntry, self.events)

                    elif sectionName == "members":
                        self.members = {}
                        for memberEntry in sectionValue:
                            self.addEntry(memberEntry[0].value, memberEntry[1], memberEntry, self.members)
                            
                    else:
                        logging.warn("Invalid section in %s (core.Interface): %s", sectionName) 


        #
        # core.Class
        #
        coreClass = findCall(tree, "core.Class")
        if coreClass:
            self.setMain("core.Class", coreClass.parent)
            
            configMap = getParameterFromCall(coreClass, 1)
            if configMap:
                for propertyInit in configMap:
                    
                    sectionName = propertyInit[0].value
                    sectionValue = propertyInit[1]
                    
                    if sectionName == "construct":
                        self.addConstructor(sectionValue, propertyInit)

                    elif sectionName == "properties":
                        self.properties = {}
                        for propertyEntry in sectionValue:
                            self.addProperty(propertyEntry[0].value, propertyEntry[1], propertyEntry, self.properties)
                    
                    elif sectionName == "events":
                        self.events = {}
                        for eventEntry in sectionValue:
                            self.addEvent(eventEntry[0].value, eventEntry[1], eventEntry, self.events)

                    elif sectionName == "members":
                        self.members = {}
                        for memberEntry in sectionValue:
                            self.addEntry(memberEntry[0].value, memberEntry[1], memberEntry, self.members)

                    else:
                        logging.warn("Invalid section in %s (core.Interface): %s", sectionName) 



    def export(self):
        
        ret = {}
        for name in self.__slots__:
            if hasattr(self, name):
                ret[name] = getattr(self, name)
                
        return ret


    def toJSON(self, format=False):
        if format:
            return json.dumps(self.export(), sort_keys=True, indent=2)
        else:
            return json.dumps(self.export())
        
        
    def toMsgpack(self):
        return msgpack.packb(self.export())
        
        
    def warn(self, message, line):
        logging.warn("%s at line %s in %s" % (message, line, self.id))


    def getDocComment(self, node, msg=None, required=True):
        comments = getattr(node, "comments", None)
        if comments:
            for comment in comments:
                if comment.variant == "doc":
                    if not comment.text and msg and required:
                        self.warn("Missing documentation text (%s)" % msg, node.line)

                    return comment

        if msg and required:
            self.warn("Missing documentation (%s)" % msg, node.line)

        return None



    def setMain(self, mainType, mainNode):
        
        callComment = self.getDocComment(mainNode, "Main")

        self.main = {
            "type" : mainType,
            "line" : mainNode.line,
            "doc" : callComment.html if callComment else None
        }


    def addProperty(self, name, valueNode, commentNode, collection):
        
        entry = collection[name] = {}
        comment = self.getDocComment(valueNode, "Property '%s'" % name)
        
        # Copy over value
        ptype = getKeyValue(valueNode, "type")
        if ptype and ptype.type == "string":
            entry["type"] = compressor.compress(ptype)
            
        pfire = getKeyValue(valueNode, "fire")
        if pfire and pfire.type == "string":
            entry["fire"] = compressor.compress(pfire)

        # Produce nice output for init value
        pinit = getKeyValue(valueNode, "init")
        if pinit:
            entry["init"] = valueToString(pinit)
        
        # Handle nullable, default value is true when an init value is there. Otherwise false.
        pnullable = getKeyValue(valueNode, "nullable")
        if pnullable:
            entry["nullable"] = pnullable.type == "true"
        elif pinit is not None and pinit.type != "null":
            entry["nullable"] = False
        else:
            entry["nullable"] = True

        # Just store whether an apply routine was defined
        papply = getKeyValue(valueNode, "apply")
        if papply and papply.type == "function":
            entry["apply"] = True
        
        # Multi Properties
        pthemeable = getKeyValue(valueNode, "themeable")
        if pthemeable and pthemeable.type == "true":
            entry["themeable"] = True
        
        pinheritable = getKeyValue(valueNode, "inheritable")
        if pinheritable and pinheritable.type == "true":
            entry["inheritable"] = True
        
        pgroup = getKeyValue(valueNode, "group")
        if pgroup and len(pgroup) > 0:
            entry["group"] = [child.value for child in pgroup]
            
            pshorthand = getKeyValue(valueNode, "shorthand")
            if pshorthand and pshorthand.type == "true":
                entry["shorthand"] = True
        


    def addConstructor(self, valueNode, commentNode):
        entry = self.constructor = {}
        
        funcParams = getParamNamesFromFunction(valueNode)
        if funcParams:
            entry["params"] = {}
            for paramName in funcParams:
                entry["params"][paramName] = {}
            
            # Use comment for enrich existing data
            comment = self.getDocComment(commentNode, "Constructor")
            if comment:
                if not comment.params:
                    self.warn("Documentation for parameters of function %s are missing" % name, valueNode.line)
                else:
                    for paramName in funcParams:
                        if paramName in comment.params:
                            entry["params"][paramName] = comment.params[paramName]
                        else:
                            self.warn("Missing documentation for parameter %s in function %s" % (paramName, name), valueNode.line)



    def addEvent(self, name, valueNode, commentNode, collection):
        entry = collection[name] = {}
        
        if valueNode.type == "dot":
            entry["type"] = assembleDot(valueNode)
        elif valueNode.type == "identifier":
            entry["type"] = valueNode.value
            
            # Try to resolve identifier with local variable assignment
            assignments, values = findAssignments(valueNode.value, valueNode)
            if assignments:
                
                # We prefer the same comment node as before as in these 
                # szenarios a reference might be used for different event types
                if not findCommentNode(commentNode):
                    commentNode = assignments[0]

                self.addEvent(name, values[0], commentNode, collection)
                return
        
        comment = self.getDocComment(commentNode, "Event '%s'" % name)
        if comment:
            
            # Prefer type but fall back to returns (if the developer has made an error here)
            if comment.type:
                entry["type"] = comment.type
            elif comment.returns:
                entry["type"] = comment.returns[0]

            if comment.html:
                entry["doc"] = comment.html



    def addEntry(self, name, valueNode, commentNode, collection):
        
        #
        # Use already existing type or get type from node info
        #
        if name in collection:
            entry = collection[name]
        else:
            entry = collection[name] = {
                "type" : nodeTypeToDocType[valueNode.type]
            }
        
        
        #
        # Store generic data like line number and visibility
        #
        entry["line"] = valueNode.line
        entry["visibility"] = getVisibility(name)
        
        if name.upper() == name:
            entry["constant"] = True
        
        
        # 
        # Complex structured types are processed in two steps
        #
        if entry["type"] == "Call" or entry["type"] == "Hook":
            
            commentNode = findCommentNode(commentNode)
            if commentNode:

                comment = self.getDocComment(commentNode, "Call/Hook '%s'" % name)
                if comment:

                    # Static type definition
                    if comment.type:
                        entry["type"] = comment.type
                        self.addEntry(name, valueNode, commentNode, collection)
                        return
                
                    else:
                    
                        # Maybe type function: We need to ignore returns etc. which are often
                        # the parent of the comment.
                        funcValueNode = findFunction(commentNode)
                        if funcValueNode:
                        
                            # Switch to function type for re-analysis
                            entry["type"] = "Function"
                            self.addEntry(name, funcValueNode, commentNode, collection)
                            return
                        
            if entry["type"] == "Call":
                
                if valueNode[0].type == "function":
                    callFunction = valueNode[0]
                
                elif valueNode[0].type == "identifier":
                    assignNodes, assignValues = findAssignments(valueNode[0].value, valueNode[0])
                    if assignNodes:
                        callFunction = assignValues[0]
                
                if callFunction:
                    # We try to analyze what the first return node returns
                    returnNode = findReturn(callFunction)
                    if returnNode and len(returnNode) > 0:
                        returnValue = returnNode[0]
                        entry["type"] = nodeTypeToDocType[returnValue.type]
                        self.addEntry(name, returnValue, returnValue, collection)
                    
            elif entry["type"] == "Hook":

                thenEntry = valueNode[1]
                thenType = nodeTypeToDocType[thenEntry.type]
                if not thenType in ("void", "null"):
                    entry["type"] = thenType
                    self.addEntry(name, thenEntry, thenEntry, collection)

                # Try second item for better data then null/void
                else:
                    elseEntry = valueNode[2]
                    elseType = nodeTypeToDocType[elseEntry.type]
                    entry["type"] = elseType
                    self.addEntry(name, elseEntry, elseEntry, collection)
                
            return
            
            
        #
        # Try to resolve identifiers
        #
        if entry["type"] == "Identifier":
            
            assignNodes, assignValues = findAssignments(valueNode.value, valueNode)
            if assignNodes:
            
                assignCommentNode = None
            
                # Find first relevant assignment with comment! Otherwise just first one.
                for assign in assignNodes:
                
                    # The parent is the relevant doc comment container
                    # It's either a "var" (declaration) or "semicolon" (assignment)
                    if getDocComment(assign):
                        assignCommentNode = assign
                        break
                    elif getDocComment(assign.parent):
                        assignCommentNode = assign.parent
                        break
                
                assignType = assignValues[0].type
                
                entry["type"] = nodeTypeToDocType[assignType]
                
                # Prefer comment from assignment, not from value if available
                self.addEntry(name, assignValues[0], assignCommentNode or assignValues[0], collection)
            
                return



        #
        # Processes special types:
        #
        # - Plus: Whether a string or number is created
        # - Object: Figures out the class instance which is created
        #
        if entry["type"] == "Plus":
            entry["type"] = detectPlusType(valueNode)
        
        elif entry["type"] == "Object":
            entry["type"] = detectObjectType(valueNode)
        
        
        #
        # Add human readable value
        #
        valueNodeHumanValue = valueToString(valueNode)
        if valueNodeHumanValue != entry["type"]:
            entry["value"] = valueNodeHumanValue
        
        
        #
        # Read data from comment and add documentation
        #
        comment = self.getDocComment(commentNode, "Member/Static %s (%s)" % (name, entry["type"]), requiresDocumentation(name))
        if comment:
            
            if comment.type:
                entry["type"] = comment.type
                
            if comment.html:
                entry["doc"] = comment.html
                
            if comment.tags:
                entry["tags"] = comment.tags
        
        
        #
        # Add additional data for function types (params, returns)
        #
        if entry["type"] == "Function":
            
            # Add basic param data
            funcParams = getParamNamesFromFunction(valueNode)
            if funcParams:
                entry["params"] = {}
                for paramName in funcParams:
                    entry["params"][paramName] = {}
            
            # Detect return type automatically
            returnNode = findReturn(valueNode)
            if returnNode and len(returnNode) > 0:
                entry["returns"] = [nodeTypeToDocType[returnNode[0].type]]

            # Use comment for enrich existing data
            if comment:
                if comment.returns:
                    entry["returns"] = comment.returns

                if funcParams:
                    if not comment.params:
                        self.warn("Documentation for parameters of function %s are missing" % name, valueNode.line)
                    else:
                        for paramName in funcParams:
                            if paramName in comment.params:
                                entry["params"][paramName] = comment.params[paramName]
                            else:
                                self.warn("Missing documentation for parameter %s in function %s" % (paramName, name), valueNode.line)


