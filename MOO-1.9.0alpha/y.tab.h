/* A Bison parser, made by GNU Bison 3.8.2.  */

/* Bison interface for Yacc-like parsers in C

   Copyright (C) 1984, 1989-1990, 2000-2015, 2018-2021 Free Software Foundation,
   Inc.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <https://www.gnu.org/licenses/>.  */

/* As a special exception, you may create a larger work that contains
   part or all of the Bison parser skeleton and distribute that work
   under terms of your choice, so long as that work isn't itself a
   parser generator using the skeleton or a modified version thereof
   as a parser skeleton.  Alternatively, if you modify or redistribute
   the parser skeleton itself, you may (at your option) remove this
   special exception, which will cause the skeleton and the resulting
   Bison output files to be licensed under the GNU General Public
   License without this special exception.

   This special exception was added by the Free Software Foundation in
   version 2.2 of Bison.  */

/* DO NOT RELY ON FEATURES THAT ARE NOT DOCUMENTED in the manual,
   especially those whose name start with YY_ or yy_.  They are
   private implementation details that can be changed or removed.  */

#ifndef YY_YY_Y_TAB_H_INCLUDED
# define YY_YY_Y_TAB_H_INCLUDED
/* Debug traces.  */
#ifndef YYDEBUG
# define YYDEBUG 0
#endif
#if YYDEBUG
extern int yydebug;
#endif

/* Token kinds.  */
#ifndef YYTOKENTYPE
# define YYTOKENTYPE
  enum yytokentype
  {
    YYEMPTY = -2,
    YYEOF = 0,                     /* "end of file"  */
    YYerror = 256,                 /* error  */
    YYUNDEF = 257,                 /* "invalid token"  */
    tCHR = 258,                    /* tCHR  */
    tINTEGER = 259,                /* tINTEGER  */
    tOBJECT = 260,                 /* tOBJECT  */
    tFLOAT = 261,                  /* tFLOAT  */
    tSTRING = 262,                 /* tSTRING  */
    tID = 263,                     /* tID  */
    tERROR = 264,                  /* tERROR  */
    tIF = 265,                     /* tIF  */
    tELSE = 266,                   /* tELSE  */
    tELSEIF = 267,                 /* tELSEIF  */
    tENDIF = 268,                  /* tENDIF  */
    tFOR = 269,                    /* tFOR  */
    tIN = 270,                     /* tIN  */
    tENDFOR = 271,                 /* tENDFOR  */
    tRETURN = 272,                 /* tRETURN  */
    tFORK = 273,                   /* tFORK  */
    tENDFORK = 274,                /* tENDFORK  */
    tWHILE = 275,                  /* tWHILE  */
    tENDWHILE = 276,               /* tENDWHILE  */
    tTRY = 277,                    /* tTRY  */
    tENDTRY = 278,                 /* tENDTRY  */
    tEXCEPT = 279,                 /* tEXCEPT  */
    tFINALLY = 280,                /* tFINALLY  */
    tANY = 281,                    /* tANY  */
    tBREAK = 282,                  /* tBREAK  */
    tCONTINUE = 283,               /* tCONTINUE  */
    tTO = 284,                     /* tTO  */
    tARROW = 285,                  /* tARROW  */
    tOR = 286,                     /* tOR  */
    tAND = 287,                    /* tAND  */
    tEQ = 288,                     /* tEQ  */
    tNE = 289,                     /* tNE  */
    tLE = 290,                     /* tLE  */
    tGE = 291,                     /* tGE  */
    tBITOR = 292,                  /* tBITOR  */
    tBITXOR = 293,                 /* tBITXOR  */
    tBITAND = 294,                 /* tBITAND  */
    tSHL = 295,                    /* tSHL  */
    tSHR = 296,                    /* tSHR  */
    tLSHR = 297,                   /* tLSHR  */
    tUNARYMINUS = 298              /* tUNARYMINUS  */
  };
  typedef enum yytokentype yytoken_kind_t;
#endif
/* Token kinds.  */
#define YYEMPTY -2
#define YYEOF 0
#define YYerror 256
#define YYUNDEF 257
#define tCHR 258
#define tINTEGER 259
#define tOBJECT 260
#define tFLOAT 261
#define tSTRING 262
#define tID 263
#define tERROR 264
#define tIF 265
#define tELSE 266
#define tELSEIF 267
#define tENDIF 268
#define tFOR 269
#define tIN 270
#define tENDFOR 271
#define tRETURN 272
#define tFORK 273
#define tENDFORK 274
#define tWHILE 275
#define tENDWHILE 276
#define tTRY 277
#define tENDTRY 278
#define tEXCEPT 279
#define tFINALLY 280
#define tANY 281
#define tBREAK 282
#define tCONTINUE 283
#define tTO 284
#define tARROW 285
#define tOR 286
#define tAND 287
#define tEQ 288
#define tNE 289
#define tLE 290
#define tGE 291
#define tBITOR 292
#define tBITXOR 293
#define tBITAND 294
#define tSHL 295
#define tSHR 296
#define tLSHR 297
#define tUNARYMINUS 298

/* Value type.  */
#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
union YYSTYPE
{
#line 72 "parser.y"

  Stmt	       *stmt;
  Expr	       *expr;
  int32_t	chr;		/* Used to carry non-ASCII characters */
  Num		integer;
  Objid		object;
  FlBox         real;
  char	       *string;
  enum error	error;
  Arg_List     *args;
  Cond_Arm     *arm;
  Except_Arm   *except;
  Scatter      *scatter;

#line 168 "y.tab.h"

};
typedef union YYSTYPE YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif


extern YYSTYPE yylval;


int yyparse (void);


#endif /* !YY_YY_Y_TAB_H_INCLUDED  */
