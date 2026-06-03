use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

declare_id!("STALECPI11111111111111111111111111111111111");

#[program]
pub mod stale_vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let state = &mut ctx.accounts.state;
        state.tracked_balance = 0;
        state.bump = *ctx.bumps.get("state").unwrap();
        Ok(())
    }

    pub fn deposit_and_track(ctx: Context<DepositAction>, amount: u64) -> Result<()> {
        let balance_before = ctx.accounts.vault.amount;

        let cpi_accounts = Transfer {
            from: ctx.accounts.user_token.to_account_info(),
            to: ctx.accounts.vault.to_account_info(),
            authority: ctx.accounts.user.to_account_info(),
        };
        let cpi_ctx = CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts);
        token::transfer(cpi_ctx, amount)?;

        let balance_after = ctx.accounts.vault.amount;
        let deposited = balance_after.wrapping_sub(balance_before);

        ctx.accounts.state.tracked_balance = ctx
            .accounts
            .state
            .tracked_balance
            .wrapping_add(deposited);

        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + State::SIZE,
        seeds = [b"state"],
        bump
    )]
    pub state: Account<'info, State>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct DepositAction<'info> {
    #[account(mut, seeds = [b"state"], bump = state.bump)]
    pub state: Account<'info, State>,
    pub user: Signer<'info>,
    #[account(mut)]
    pub user_token: Account<'info, TokenAccount>,
    #[account(mut)]
    pub vault: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct State {
    pub tracked_balance: u64,
    pub bump: u8,
}

impl State {
    pub const SIZE: usize = 8 + 1;
}
